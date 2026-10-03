"""راه‌اندازی خودکار روی Railway با توکن حساب کاربر (GraphQL API).

کاربر فقط یک **API Token** از Railway می‌دهد؛ این ماژول بقیه‌ی کارها را انجام می‌دهد:

1. پروژه می‌سازد (`projectCreate`)
2. سرویس پنل را از ریپو می‌سازد، Root Directory را `panel` می‌گذارد،
   یک **Volume روی /data** وصل می‌کند، رمز ادمین تصادفی می‌سازد، متغیرها را ست می‌کند
   و دامنه‌ی عمومی می‌گیرد (`serviceDomainCreate`)
3. برای هر لوکیشن، یک سرویس نود در ریجن انتخابی می‌سازد، توکن نود می‌گیرد،
   متغیرهای نود را ست می‌کند، دامنه می‌گیرد و به پنل معرفی می‌کند
4. در پایان: آدرس پنل + یوزر/پسورد ادمین + لینک ساب

همه‌ی مراحل قابل‌تکرار (idempotent) هستند: سرویس/دامنه‌ی موجود دوباره ساخته نمی‌شود.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time

import httpx

logger = logging.getLogger("mlp.panel.railway")

API_URL = "https://backboard.railway.com/graphql/v2"

# ── کوئری‌ها ──
Q_ME = "query { me { id name email } }"

M_PROJECT = """
mutation projectCreate($input: ProjectCreateInput!) {
  projectCreate(input: $input) { id name }
}
"""

M_SERVICE = """
mutation serviceCreate($input: ServiceCreateInput!) {
  serviceCreate(input: $input) { id name }
}
"""

M_UPDATE_INSTANCE = """
mutation serviceInstanceUpdate($serviceId: String!, $environmentId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $serviceId, environmentId: $environmentId, input: $input)
}
"""

M_VARIABLES = """
mutation variableCollectionUpsert($input: VariableCollectionUpsertInput!) {
  variableCollectionUpsert(input: $input)
}
"""

M_DOMAIN = """
mutation serviceDomainCreate($input: ServiceDomainCreateInput!) {
  serviceDomainCreate(input: $input) { domain }
}
"""

Q_PROJECT = """
query project($id: String!) {
  project(id: $id) {
    id name
    environments(first: 5) { edges { node { id name } } }
    services(first: 50) { edges { node { id name } } }
  }
}
"""

M_VOLUME = """
mutation volumeCreate($input: VolumeCreateInput!) {
  volumeCreate(input: $input) { id name }
}
"""

M_REDEPLOY = """
mutation serviceInstanceRedeploy($serviceId: String!, $environmentId: String!) {
  serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
}
"""


class RailwayError(RuntimeError):
    pass


class Railway:
    def __init__(self, token: str, timeout: float = 45.0) -> None:
        if not token or len(token) < 10:
            raise RailwayError("توکن Railway نامعتبر است")
        self.token = token.strip()
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "Railway":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def gql(self, query: str, variables: dict | None = None) -> dict:
        resp = await self._client.post(
            API_URL,
            json={"query": query, "variables": variables or {}},
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "MLP-Panel/1.1",
            },
        )
        if resp.status_code == 401:
            raise RailwayError("توکن Railway پذیرفته نشد (۴۰۱)")
        if resp.status_code == 429:
            raise RailwayError("Railway محدودسازی نرخ کرد؛ چند لحظه بعد دوباره امتحان کن")
        try:
            data = resp.json()
        except Exception as exc:
            raise RailwayError(f"پاسخ نامعتبر از Railway (HTTP {resp.status_code})") from exc
        if data.get("errors"):
            message = "; ".join(str(e.get("message"))[:200] for e in data["errors"])
            raise RailwayError(message)
        return data.get("data") or {}

    # ── شناسایی ──
    async def me(self) -> dict:
        return (await self.gql(Q_ME)).get("me") or {}

    # ── ساخت‌وساز ──
    async def create_project(self, name: str, workspace_id: str = "") -> dict:
        payload: dict = {"name": name}
        if workspace_id:
            payload["workspaceId"] = workspace_id
        data = await self.gql(M_PROJECT, {"input": payload})
        return data.get("projectCreate") or {}

    async def project(self, project_id: str) -> dict:
        return (await self.gql(Q_PROJECT, {"id": project_id})).get("project") or {}

    async def environment_id(self, project_id: str) -> str:
        project = await self.project(project_id)
        edges = ((project.get("environments") or {}).get("edges") or [])
        if not edges:
            raise RailwayError("محیط production در این پروژه پیدا نشد")
        for edge in edges:
            node = edge.get("node") or {}
            if (node.get("name") or "").lower() in ("production", "prod"):
                return node["id"]
        return edges[0]["node"]["id"]

    async def services(self, project_id: str) -> list[dict]:
        project = await self.project(project_id)
        return [edge["node"] for edge in ((project.get("services") or {}).get("edges") or [])]

    async def create_service(self, project_id: str, name: str, repo: str, branch: str = "main") -> dict:
        data = await self.gql(M_SERVICE, {"input": {
            "projectId": project_id,
            "name": name,
            "source": {"repo": repo, "branch": branch or "main"},
        }})
        return data.get("serviceCreate") or {}

    async def configure_service(self, service_id: str, environment_id: str, root_directory: str,
                               region: str = "", start_command: str = "", dockerfile_path: str = "") -> None:
        payload: dict = {}
        if root_directory:
            payload["rootDirectory"] = root_directory
        if region:
            payload["region"] = region
        if start_command:
            payload["startCommand"] = start_command
        if dockerfile_path:
            payload["dockerfilePath"] = dockerfile_path
        if not payload:
            return
        await self.gql(M_UPDATE_INSTANCE, {
            "serviceId": service_id, "environmentId": environment_id, "input": payload,
        })

    async def set_variables(self, project_id: str, environment_id: str, service_id: str,
                            variables: dict[str, str]) -> None:
        await self.gql(M_VARIABLES, {"input": {
            "projectId": project_id,
            "environmentId": environment_id,
            "serviceId": service_id,
            "variables": {k: str(v) for k, v in variables.items()},
        }})

    async def create_volume(self, project_id: str, environment_id: str, service_id: str,
                            mount_path: str = "/data") -> dict:
        data = await self.gql(M_VOLUME, {"input": {
            "projectId": project_id, "environmentId": environment_id,
            "serviceId": service_id, "mountPath": mount_path,
        }})
        return data.get("volumeCreate") or {}

    async def create_domain(self, environment_id: str, service_id: str, port: int = 8080) -> str:
        """دامنه‌ی عمومی سرویس (به پورت داخلی سرویس وصل می‌شود)."""
        target_port = int(port)
        for variant in (
            {"environmentId": environment_id, "serviceId": service_id, "targetPort": target_port},
            {"environmentId": environment_id, "serviceId": service_id},
        ):
            try:
                data = await self.gql(M_DOMAIN, {"input": variant})
                domain = (data.get("serviceDomainCreate") or {}).get("domain") or ""
                if domain:
                    return domain
            except RailwayError as exc:
                last = exc
                continue
        raise RailwayError(f"ساخت دامنه ناموفق بود: {last}" if 'last' in dir() else "ساخت دامنه ناموفق بود")

    async def redeploy(self, service_id: str, environment_id: str) -> None:
        try:
            await self.gql(M_REDEPLOY, {"serviceId": service_id, "environmentId": environment_id})
        except RailwayError as exc:
            logger.warning("redeploy failed: %s", exc)

    async def wait_domain(self, domain: str, path: str = "/healthz", timeout: float = 240.0) -> bool:
        """منتظر می‌ماند سرویس واقعاً بالا بیاید."""
        deadline = time.time() + timeout
        url = f"https://{domain}{path}"
        while time.time() < deadline:
            try:
                resp = await self._client.get(url, timeout=10.0)
                if resp.status_code < 500:
                    return True
            except Exception:
                pass
            await asyncio.sleep(6)
        return False


def detected_repo() -> str:
    """ریپویی که خودِ پنل از آن دیپلوی شده (Railway این‌ها را تزریق می‌کند)."""
    owner = os.environ.get("RAILWAY_GIT_REPO_OWNER", "").strip()
    name = os.environ.get("RAILWAY_GIT_REPO_NAME", "").strip()
    if owner and name:
        return f"{owner}/{name}"
    return os.environ.get("MLP_REPO", "").strip() or DEFAULT_REPO


def detected_branch() -> str:
    """شاخه‌ای که کد فعلی از آن آمده — مهم: اگر main خالی باشد، همین باعث خطای بیلد می‌شود."""
    return (os.environ.get("RAILWAY_GIT_BRANCH") or "").strip() or "main"


def random_password(length: int = 14) -> str:
    alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


DEFAULT_REPO = "mazodimobinhost-creator/test-real"


async def auto_deploy(
    token: str,
    *,
    repo: str = "",
    branch: str = "main",
    project_name: str = "",
    workspace_id: str = "",
    panel_name: str = "panel",
    admin_password: str = "",
    node_specs: list[dict] | None = None,
    panel_url: str = "",
    wait: bool = True,
) -> dict:
    """همه‌چیز را می‌سازد و گزارش نهایی (آدرس پنل، یوزر/پسورد، لوکیشن‌ها) را برمی‌گرداند.

    `node_specs` نمونه: `[{"name": "Germany", "flag": "🇩🇪", "region": "europe-west3"}]`
    """
    repo = (repo or detected_repo()).strip().replace("https://github.com/", "").strip("/")
    branch = (branch or detected_branch()).strip() or "main"
    password = admin_password or random_password()
    project_name = project_name or f"mlp-{secrets.token_hex(2)}"
    steps: list[dict] = []
    result: dict = {"ok": False, "steps": steps, "project": project_name, "repo": repo}

    def log(message: str, level: str = "info") -> None:
        steps.append({"at": int(time.time()), "level": level, "message": message})
        logger.info("[auto-deploy] %s", message)

    client = Railway(token)
    try:
        user = await client.me()
        log(f"اتصال به حساب Railway: {user.get('email') or user.get('name') or 'ok'}")

        project = await client.create_project(project_name, workspace_id)
        project_id = project.get("id")
        if not project_id:
            raise RailwayError("ساخت پروژه ناموفق بود")
        env_id = await client.environment_id(project_id)
        result["project_id"] = project_id
        log(f"پروژه «{project_name}» ساخته شد", "ok")

        # ── سرویس پنل ──
        panel_service = await client.create_service(project_id, panel_name, repo, branch)
        panel_id = panel_service.get("id") or ""
        await client.configure_service(panel_id, env_id, "panel")
        await client.create_volume(project_id, env_id, panel_id, "/data")
        public = panel_url.strip().rstrip("/")
        panel_vars = {
            "MLP_ADMIN_USER": "admin",
            "MLP_ADMIN_PASSWORD": password,
            "MLP_DATA_DIR": "/data",
            "MLP_REPO_URL": f"https://github.com/{repo}",
        }
        if public:
            panel_vars["MLP_PUBLIC_URL"] = public
        await client.set_variables(project_id, env_id, panel_id, panel_vars)
        domain = public.replace("https://", "").replace("http://", "") if public else ""
        if not domain:
            domain = await client.create_domain(env_id, panel_id, 8080)
        result["panel_domain"] = domain
        result["panel_url"] = f"https://{domain}"
        log(f"سرویس پنل ساخته شد و دامنه گرفت: {domain}", "ok")

        if wait:
            alive = await client.wait_domain(domain)
            log("پنل پاسخ داد ✅" if alive else "پنل هنوز بالا نیامده (چند دقیقه دیگر چک کن)", "ok" if alive else "warn")

        # ── سرویس‌های نود ──
        specs = node_specs if node_specs is not None else [
            {"name": "Germany", "flag": "🇩🇪", "region": "europe-west3"},
            {"name": "Netherlands", "flag": "🇳🇱", "region": "europe-west4"},
        ]
        nodes: list[dict] = []
        for spec in specs:
            name = str(spec.get("name") or "node")
            node_service = await client.create_service(project_id, f"node-{name.lower()}", repo, branch)
            node_id = node_service.get("id") or ""
            await client.configure_service(node_id, env_id, "node", region=str(spec.get("region") or ""),
                                           dockerfile_path=str(spec.get("dockerfile") or ""))
            node_domain = await client.create_domain(env_id, node_id, 8080)
            await client.set_variables(project_id, env_id, node_id, {
                "MLP_PANEL_URL": result["panel_url"],
                "MLP_NODE_NAME": name,
                "MLP_NODE_FLAG": str(spec.get("flag") or "🌍"),
                "MLP_ENGINE": str(spec.get("engine") or "python"),
                "MLP_DECOY": str(spec.get("decoy") or "auto"),
                "MLP_EGRESS": str(spec.get("egress") or "direct"),
            })
            node = {"name": name, "flag": spec.get("flag") or "🌍", "region": spec.get("region") or "",
                    "domain": node_domain, "service_id": node_id}
            nodes.append(node)
            log(f"سرویس نود «{name}» ساخته شد ({spec.get('region') or 'ریجن پیش‌فرض'})", "ok")
        result["nodes"] = nodes
        result["ok"] = True
        log("راه‌اندازی خودکار تمام شد", "ok")

        # ── معرفی لوکیشن‌ها به پنل و گرفتن توکن هر نود ──
        if wait and result.get("panel_url"):
            from . import store

            try:
                async with httpx.AsyncClient(timeout=25.0) as api:
                    login = await api.post(f"{result['panel_url']}/api/admin/login",
                                           json={"username": "admin", "password": password})
                    cookies = login.cookies
                    created = []
                    for node in nodes:
                        resp = await api.post(f"{result['panel_url']}/api/admin/locations", json={
                            "name": node["name"], "flag": node["flag"], "region": node["region"],
                            "host": node["domain"], "transports": ["ws", "xhttp"], "engine": "python",
                        }, cookies=cookies)
                        if resp.status_code == 200:
                            data = resp.json()
                            token = ""
                            for line in (data.get("env") or "").splitlines():
                                if line.startswith("MLP_NODE_TOKEN="):
                                    token = line.split("=", 1)[1]
                            created.append({"name": node["name"], "token": token})
                    result["node_tokens"] = len(created)
                    log(f"{len(created)} لوکیشن در پنل ثبت شد", "ok")
            except Exception as exc:
                log(f"ثبت خودکار لوکیشن‌ها ناموفق بود ({type(exc).__name__}) — دستی از تب لوکیشن‌ها بساز", "warn")

        result["admin"] = {"username": "admin", "password": password}
        result["env_lines"] = "\n".join([
            "MLP_ADMIN_USER=admin",
            f"MLP_ADMIN_PASSWORD={password}",
            "MLP_DATA_DIR=/data",
            f"PORT=8080   # پنل روی همین پورت بالا می‌آید (Railway خودش تشخیص می‌دهد)",
        ])
        return result
    except Exception as exc:
        log(f"خطا: {type(exc).__name__}: {exc}", "error")
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
    finally:
        await client.close()


def deploy_plan(repo: str = "", node_specs: list[dict] | None = None, branch: str = "") -> dict:
    """پیش‌نمایش کاری که قرار است انجام شود (برای نمایش در پنل قبل از اجرا)."""
    repo = (repo or detected_repo()).strip().replace("https://github.com/", "").strip("/")
    branch = (branch or detected_branch()).strip() or "main"
    specs = node_specs or [
        {"name": "Germany", "flag": "🇩🇪", "region": "europe-west3"},
        {"name": "Netherlands", "flag": "🇳🇱", "region": "europe-west4"},
    ]
    return {
        "repo": repo,
        "branch": branch,
        "detected": {
            "repo": detected_repo(),
            "branch": detected_branch(),
            "source": "Railway env" if os.environ.get("RAILWAY_GIT_REPO_NAME") else "پیش‌فرض",
        },
        "panel": {
            "service": "panel", "root_directory": "panel", "port": 8080,
            "volume": "/data", "dockerfile": "panel/Dockerfile",
            "variables": ["MLP_ADMIN_USER", "MLP_ADMIN_PASSWORD (تصادفی)", "MLP_DATA_DIR=/data", "PORT=8080"],
        },
        "nodes": [
            {**spec, "service": f"node-{str(spec.get('name', 'node')).lower()}",
             "root_directory": "node", "port": 8080,
             "variables": ["MLP_PANEL_URL", "MLP_NODE_TOKEN", "MLP_NODE_NAME", "MLP_NODE_FLAG",
                           "MLP_ENGINE", "MLP_DECOY", "MLP_EGRESS"]}
            for spec in specs
        ],
        "estimated_minutes": 3 + len(specs),
        "note": "همه‌ی سرویس‌ها از همان ریپو و همان شاخه‌ی این پنل ساخته می‌شوند؛ نیازی به کار دستی نیست.",
        "branch_warning": (
            f"شاخه‌ی انتخاب‌شده «{branch}» است. اگر در این شاخه کد نباشد و فقط README داشته باشد، "
            "Railway با خطای «failed to prepare the build» بالا نمی‌آید — شاخه‌ای را بده که کد داخلش است."
        ),
    }


def to_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1)
