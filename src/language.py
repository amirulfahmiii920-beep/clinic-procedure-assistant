"""Detect whether a question is in Malay or English, and the fixed replies in each language."""
import re

MALAY_MARKERS = {
    "apa", "apakah", "bila", "berapa", "bagaimana", "macam", "mana", "saya", "kami", "boleh", "perlu",
    "kena", "untuk", "dengan", "tak", "tidak", "buka", "tutup", "hari", "pukul", "bayar", "bawa",
    "daftar", "lupa", "lewat", "temujanji", "doktor", "ada", "ke", "kah", "ini", "itu", "jika", "kalau",
    "di", "yang", "dan", "atau", "pada", "dari", "nak", "sudah", "belum", "dapat", "tempat", "berbayar",
    "dokumen", "dibawa", "pesakit", "kad", "warga", "emas", "percuma", "kena", "macam", "mana",
}


def detect_language(text: str) -> str:
    words = re.findall(r"[a-z]+", text.lower())
    hits = sum(w in MALAY_MARKERS for w in words)
    return "ms" if hits >= 2 or (words and hits / len(words) >= 0.34) else "en"


MESSAGES = {
    "NOT_FOUND": {
        "en": "The clinic's SOPs don't cover this question, so I can't answer it. Please ask at the registration counter.",
        "ms": "SOP klinik tidak menyentuh soalan ini, jadi saya tidak dapat menjawabnya. Sila tanya di kaunter pendaftaran.",
    },
    "REFUSED_MEDICAL": {
        "en": ("I can only answer questions about the clinic's procedures, such as registration, opening hours, "
               "fees and appointments. I can't give advice about medicines, symptoms or treatment. Please ask a "
               "doctor or pharmacist at the clinic. If it is an emergency, go straight to the treatment room or call 999."),
        "ms": ("Saya hanya boleh menjawab soalan tentang prosedur klinik, seperti pendaftaran, waktu operasi, bayaran "
               "dan temujanji. Saya tidak boleh memberi nasihat tentang ubat, simptom atau rawatan. Sila tanya doktor "
               "atau ahli farmasi di klinik. Jika kecemasan, terus ke bilik rawatan atau hubungi 999."),
    },
    "BLOCKED_INPUT": {
        "en": "I can't process this message. Please ask a short question about the clinic's procedures.",
        "ms": "Saya tidak dapat memproses mesej ini. Sila tanya soalan ringkas tentang prosedur klinik.",
    },
    "BLOCKED_OUTPUT": {
        "en": ("The drafted answer contained medical advice, so it was withheld. Please ask a doctor or pharmacist "
               "at the clinic."),
        "ms": ("Jawapan yang dihasilkan mengandungi nasihat perubatan, jadi ia tidak dipaparkan. Sila tanya doktor "
               "atau ahli farmasi di klinik."),
    },
}


def message(key: str, lang: str) -> str:
    return MESSAGES[key][lang]
