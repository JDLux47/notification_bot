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


# Экранирует спецсимволы для Markdown
def escape_markdown_v2(text: str) -> str:
    chars_to_escape = r'_ * [ ] ( ) ~ ` > # + - = | { } . !'.split()
    for char in chars_to_escape:
        text = text.replace(char, rf'\{char}')
    return text