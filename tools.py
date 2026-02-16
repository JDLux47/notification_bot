import json
import os
from datetime import datetime
from settings import settings


# Работа с JSON
def load_shifts():
    if os.path.exists(settings.DATA_FILE):
        with open(settings.DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_shifts(shifts):
    with open(settings.DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(shifts, f, ensure_ascii=False, indent=2)


# Получить менеджера по времени начала смены
def get_shift_start_time():
    now = datetime.now().strftime("%H:%M")
    shifts = load_shifts()

    # Проверяем смены, начинающиеся точно сейчас
    for shift in shifts:
        if shift["start_time"] == now:
            return shift["username"]
    return None