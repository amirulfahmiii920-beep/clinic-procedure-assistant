"""Deterministic tool: is the clinic open at a given time?

The opening rules come from SOP-02. Python does the time arithmetic, not the language
model, so "open now?" is answered the same way every time.
"""
import re
from datetime import datetime, time, timedelta, timezone

MYT = timezone(timedelta(hours=8))  # Malaysia time, UTC+8 (no daylight saving)

# Mon=0 ... Sun=6. Each entry is a list of (open, close) sessions, from SOP-02 Section 2.
SESSIONS = {
    0: [(time(8, 0), time(13, 0)), (time(14, 0), time(17, 0))],
    1: [(time(8, 0), time(13, 0)), (time(14, 0), time(17, 0))],
    2: [(time(8, 0), time(13, 0)), (time(14, 0), time(17, 0))],
    3: [(time(8, 0), time(13, 0)), (time(14, 0), time(17, 0))],
    4: [(time(8, 0), time(12, 15)), (time(14, 45), time(17, 0))],
    5: [], 6: [],
}
REGISTRATION_CUTOFF = time(16, 30)  # SOP-01 Section 5 / SOP-02 Section 5

OPEN_NOW = re.compile(r"\b(open|closed?)\b.*\b(now|right now|today|at the moment|currently)\b"
                      r"|\b(now|currently)\b.*\b(open|closed?)\b"
                      r"|\b(buka|tutup)\b.*\b(sekarang|hari ini|tak)\b|\bsekarang\b.*\b(buka|tutup)\b", re.I)


def asks_if_open_now(question: str) -> bool:
    return bool(OPEN_NOW.search(question))


def check_clinic_open(now: datetime | None = None) -> dict:
    now = (now or datetime.now(MYT)).astimezone(MYT)
    t, day = now.time(), now.weekday()
    sessions = SESSIONS[day]
    is_open = any(start <= t < end for start, end in sessions)
    if day >= 5:
        state = "CLOSED_WEEKEND"
    elif is_open:
        state = "OPEN"
    elif sessions and t < sessions[0][0]:
        state = "NOT_YET_OPEN"
    elif sessions and t >= sessions[-1][1]:
        state = "CLOSED_FOR_THE_DAY"
    else:
        state = "BREAK"
    return {
        "checked_at": now.strftime("%A %d %B %Y, %I:%M %p"),
        "state": state,
        "registration_open": is_open and t < REGISTRATION_CUTOFF,
        "sessions_today": [f"{s.strftime('%I:%M %p')} to {e.strftime('%I:%M %p')}" for s, e in sessions],
    }


def describe(result: dict) -> str:
    state = result["state"]
    hours = " and ".join(result["sessions_today"])
    if state == "OPEN":
        msg = f"Yes, the clinic is open now ({result['checked_at']}). Today's hours: {hours}."
        if not result["registration_open"]:
            msg += " Registration has closed for today (it closes at 4:30 pm)."
    elif state == "CLOSED_WEEKEND":
        msg = (f"No. The clinic is closed on weekends ({result['checked_at']}). "
               "Go to the Emergency Department of Hospital Daerah Mawar for urgent care.")
    elif state == "NOT_YET_OPEN":
        msg = f"Not yet. It is {result['checked_at']}. Today's hours: {hours}."
    elif state == "BREAK":
        msg = (f"The clinic is on its break right now ({result['checked_at']}). "
               f"Today's hours: {hours}. Registered patients are still seen during the break.")
    else:
        msg = (f"No, the clinic has closed for today ({result['checked_at']}). "
               "For emergencies, go to the Emergency Department of Hospital Daerah Mawar.")
    return msg + " This check does not know about public holidays, when the clinic is also closed."


def describe_ms(result: dict) -> str:
    state = result["state"]
    hours = " dan ".join(result["sessions_today"])
    when = result["checked_at"]
    if state == "OPEN":
        msg = f"Ya, klinik dibuka sekarang ({when}). Waktu hari ini: {hours}."
        if not result["registration_open"]:
            msg += " Pendaftaran untuk hari ini sudah ditutup (ditutup pada 4:30 petang)."
    elif state == "CLOSED_WEEKEND":
        msg = (f"Tidak. Klinik ditutup pada hujung minggu ({when}). "
               "Untuk rawatan segera, pergi ke Jabatan Kecemasan Hospital Daerah Mawar.")
    elif state == "NOT_YET_OPEN":
        msg = f"Belum dibuka. Sekarang {when}. Waktu hari ini: {hours}."
    elif state == "BREAK":
        msg = (f"Klinik sedang berehat sekarang ({when}). Waktu hari ini: {hours}. "
               "Pesakit yang sudah mendaftar masih dirawat semasa rehat.")
    else:
        msg = (f"Tidak, klinik sudah ditutup untuk hari ini ({when}). "
               "Untuk kecemasan, pergi ke Jabatan Kecemasan Hospital Daerah Mawar.")
    return msg + " Semakan ini tidak mengambil kira cuti umum, apabila klinik juga ditutup."
