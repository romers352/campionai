"""Deterministic crisis hotline directory by country (guaranteed safety fallback)."""

HOTLINES = {
    "US": [
        {"name": "988 Suicide & Crisis Lifeline", "number": "988", "text": "Text 988", "hours": "24/7"},
        {"name": "Crisis Text Line", "number": "Text HOME to 741741", "hours": "24/7"},
    ],
    "GB": [
        {"name": "Samaritans", "number": "116 123", "hours": "24/7"},
        {"name": "SHOUT Crisis Text Line", "number": "Text SHOUT to 85258", "hours": "24/7"},
    ],
    "IN": [
        {"name": "KIRAN Mental Health Helpline", "number": "1800-599-0019", "hours": "24/7"},
        {"name": "AASRA", "number": "+91-9820466726", "hours": "24/7"},
        {"name": "Tele-MANAS", "number": "14416", "hours": "24/7"},
    ],
    "NP": [
        {"name": "Nepal Suicide Prevention Hotline", "number": "1166", "hours": "24/7"},
        {"name": "TUTH Suicide Hotline", "number": "+977-9840021600", "hours": "24/7"},
    ],
    "CA": [
        {"name": "Talk Suicide Canada", "number": "1-833-456-4566", "hours": "24/7"},
        {"name": "9-8-8 Suicide Crisis Helpline", "number": "988", "hours": "24/7"},
    ],
    "AU": [
        {"name": "Lifeline Australia", "number": "13 11 14", "hours": "24/7"},
        {"name": "Beyond Blue", "number": "1300 22 4636", "hours": "24/7"},
    ],
    "IE": [
        {"name": "Samaritans Ireland", "number": "116 123", "hours": "24/7"},
        {"name": "Pieta House", "number": "1800 247 247", "hours": "24/7"},
    ],
    "NZ": [
        {"name": "1737 Need to Talk", "number": "1737", "hours": "24/7"},
        {"name": "Lifeline Aotearoa", "number": "0800 543 354", "hours": "24/7"},
    ],
    "DE": [
        {"name": "Telefonseelsorge", "number": "0800 111 0 111", "hours": "24/7"},
    ],
    "FR": [
        {"name": "3114 Numéro national de prévention du suicide", "number": "3114", "hours": "24/7"},
    ],
    "ZA": [
        {"name": "SADAG Suicide Crisis Line", "number": "0800 567 567", "hours": "24/7"},
    ],
}

INTERNATIONAL_FALLBACK = [
    {"name": "Find A Helpline (international directory)", "number": "findahelpline.com", "hours": "24/7"},
    {"name": "Befrienders Worldwide", "number": "befrienders.org", "hours": "24/7"},
    {"name": "Emergency Services", "number": "Local emergency number (e.g. 911 / 112 / 999)", "hours": "24/7"},
]

COUNTRY_NAMES = {
    "US": "United States", "GB": "United Kingdom", "IN": "India", "NP": "Nepal",
    "CA": "Canada", "AU": "Australia", "IE": "Ireland", "NZ": "New Zealand",
    "DE": "Germany", "FR": "France", "ZA": "South Africa",
}


def get_hotlines(country_code: str | None):
    if not country_code:
        return INTERNATIONAL_FALLBACK
    code = country_code.strip().upper()
    lines = HOTLINES.get(code)
    if lines:
        return lines + [INTERNATIONAL_FALLBACK[-1]]
    return INTERNATIONAL_FALLBACK


def country_list():
    return [{"code": c, "name": n} for c, n in sorted(COUNTRY_NAMES.items(), key=lambda x: x[1])]
