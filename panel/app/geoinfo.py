"""نگاشت کد کشور/ریجن → فلگ و نام فارسی (سمت پنل)."""

from __future__ import annotations

FLAG_FALLBACK = "🌍"

COUNTRY_FA = {
    "DE": "آلمان", "NL": "هلند", "FR": "فرانسه", "GB": "انگلستان", "US": "آمریکا",
    "CA": "کانادا", "TR": "ترکیه", "IR": "ایران", "AE": "امارات", "RU": "روسیه",
    "SE": "سوئد", "FI": "فینلاند", "PL": "لهستان", "AT": "اتریش", "CH": "سوئیس",
    "IT": "ایتالیا", "ES": "اسپانیا", "IN": "هند", "SG": "سنگاپور", "JP": "ژاپن",
    "KR": "کره جنوبی", "AU": "استرالیا", "BR": "برزیل", "IE": "ایرلند", "BE": "بلژیک",
    "DK": "دانمارک", "NO": "نروژ", "CZ": "چک", "RO": "رومانی", "UA": "اوکراین",
    "HK": "هنگ‌کنگ", "CN": "چین", "IL": "اسرائیل", "SA": "عربستان", "QA": "قطر",
    "KW": "کویت", "OM": "عمان", "BH": "بحرین", "AM": "ارمنستان", "GE": "گرجستان",
    "AZ": "آذربایجان", "KZ": "قزاقستان", "PK": "پاکستان", "IQ": "عراق", "SY": "سوریه",
    "LB": "لبنان", "JO": "اردن", "EG": "مصر", "ZA": "آفریقای جنوبی", "MX": "مکزیک",
    "AR": "آرژانتین", "CL": "شیلی", "NZ": "نیوزیلند", "MY": "مالزی", "TH": "تایلند",
    "VN": "ویتنام", "ID": "اندونزی", "TW": "تایوان", "PH": "فیلیپین", "GR": "یونان",
    "PT": "پرتغال", "HU": "مجارستان", "BG": "بلغارستان", "RS": "صربستان", "LT": "لیتوانی",
    "LV": "لتونی", "EE": "استونی", "SK": "اسلواکی", "SI": "اسلوونی", "HR": "کرواسی",
    "MD": "مولداوی", "BY": "بلاروس", "CY": "قبرس", "MT": "مالت", "IS": "ایسلند",
    "LU": "لوکزامبورگ", "AL": "آلبانی", "MK": "مقدونیه", "BA": "بوسنی", "ME": "مونته‌نگرو",
}

# ریجن‌های Railway → کشور/شهر
RAILWAY_REGIONS = {
    "europe-west4": ("NL", "🇳🇱", "Amsterdam"),
    "europe-west3": ("DE", "🇩🇪", "Frankfurt"),
    "europe-west2": ("GB", "🇬🇧", "London"),
    "europe-west1": ("BE", "🇧🇪", "Brussels"),
    "us-east4": ("US", "🇺🇸", "Virginia"),
    "us-west2": ("US", "🇺🇸", "Los Angeles"),
    "us-east1": ("US", "🇺🇸", "South Carolina"),
    "us-central1": ("US", "🇺🇸", "Iowa"),
    "asia-southeast1": ("SG", "🇸🇬", "Singapore"),
    "asia-south1": ("IN", "🇮🇳", "Mumbai"),
    "asia-northeast3": ("KR", "🇰🇷", "Seoul"),
    "southamerica-east1": ("BR", "🇧🇷", "São Paulo"),
    "australia-southeast1": ("AU", "🇦🇺", "Sydney"),
}

# فهرست ریجن‌ها برای فرم راه‌اندازی خودکار
REGION_CHOICES = [
    ("europe-west4", "🇳🇱 آمستردام (هلند) — پیشنهاد برای ایران"),
    ("europe-west3", "🇩🇪 فرانکفورت (آلمان)"),
    ("europe-west2", "🇬🇧 لندن (انگلستان)"),
    ("europe-west1", "🇧🇪 بروکسل (بلژیک)"),
    ("us-east4", "🇺🇸 ویرجینیا (آمریکا)"),
    ("us-west2", "🇺🇸 لس‌آنجلس (آمریکا)"),
    ("asia-southeast1", "🇸🇬 سنگاپور"),
    ("asia-south1", "🇮🇳 هند"),
    ("asia-northeast3", "🇰🇷 کره جنوبی"),
    ("southamerica-east1", "🇧🇷 برزیل"),
    ("australia-southeast1", "🇦🇺 استرالیا"),
]


def flag_for(country_code: str) -> str:
    code = (country_code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return FLAG_FALLBACK
    return chr(0x1F1E6 + ord(code[0]) - 65) + chr(0x1F1E6 + ord(code[1]) - 65)


def railway_region_hint(region: str) -> dict:
    code, flag, city = RAILWAY_REGIONS.get((region or "").strip(), ("", FLAG_FALLBACK, ""))
    return {"country_code": code, "flag": flag, "city": city, "country": COUNTRY_FA.get(code, "")}
