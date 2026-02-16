import re
import threading
import time
import telebot
from telebot import types
from logger import setup_logger
from datetime import datetime
from settings import settings
from tools import get_shift_start_time, load_shifts, save_shifts

logger = setup_logger()
user_states = {}

bot = telebot.TeleBot(settings.BOT_TOKEN)

# Пинг смены в группу
def ping_shift_start():
    username = get_shift_start_time()

    if username:
        message = f"""
**Смена ответственного!**
{datetime.now().strftime('%d.%m %H:%M')}
@{username} твоя очередь!
        """
        try:
            bot.send_message(settings.GROUP_CHAT_ID, message, parse_mode='Markdown', disable_web_page_preview=True)
            logger.info(f"Ping shift start: @{username} in {datetime.now().strftime('%H:%M')}")
        except Exception as e:
            logger.info(f"Ping error: {e}")


# Главное меню для админа
@bot.message_handler(commands=['start'], func=lambda m: m.from_user.id in settings.ADMIN_IDS)
def admin_start(message):
    logger.info(f"Admin {message.from_user.id} opened main menu")
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Добавить смену")
    markup.add("График")
    markup.add("Редактировать")
    markup.add("Удалить")

    bot.send_message(message.chat.id,
                     "**Добро пожаловать в напоминателя!**\n"
                     "Вам открыт доступ к админ-панели",
                     parse_mode='Markdown', reply_markup=markup)


# Добавить смену
@bot.message_handler(func=lambda m: m.from_user.id in settings.ADMIN_IDS and m.text == "Добавить смену")
def add_shift_start(message):
    logger.info(f"Admin {message.from_user.id} started adding shift")
    user_states[message.from_user.id] = {"stage": "waiting_time"}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Отмена")

    bot.send_message(message.chat.id,
                     "**Добавление смены**\n\n"
                     "**Шаг 1/2:** Введите время смены:\n"
                     "Например: `17:00-19:00`",
                     parse_mode='Markdown', reply_markup=markup)


# График - последовательно по времени
@bot.message_handler(func=lambda m: m.from_user.id in settings.ADMIN_IDS and m.text == "График")
def show_schedule(message):
    logger.info(f"Admin {message.from_user.id} requested schedule")
    shifts = load_shifts()
    logger.info(f"Found {len(shifts)} shifts in schedule")

    if not shifts:
        text = "**График пуст**\n\nНажмите «Добавить смену»"
    else:
        shifts_sorted = sorted(shifts, key=lambda x: x['start_time'])

        text = "**📋 График дежурств (по порядку):**```\n"
        text += f"{'Время':<12} {'Менеджер':<15}\n"
        text += f"{'-' * 12} {'-' * 15}\n"

        for shift in shifts_sorted:
            time_range = f"{shift['start_time']}-{shift['end_time']}"
            text += f"{time_range:<12} @{shift['username']:<15}\n"
        text += "```"

        logger.info(f"Schedule sorted by time: {len(shifts_sorted)} shifts")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Добавить смену", "Редактировать")
    markup.add("График", "Удалить")

    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)


# Редактировать график
@bot.message_handler(func=lambda m: m.from_user.id in settings.ADMIN_IDS and m.text == "Редактировать")
def edit_shift_menu(message):
    logger.info(f"Admin {message.from_user.id} opened edit menu")
    shifts = load_shifts()

    if not shifts:
        logger.info("Edit menu: no shifts found")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Добавить смену")
        markup.add("График")
        markup.add("Редактировать")
        markup.add("Удалить")
        bot.send_message(message.chat.id, "**График пуст!**\nДобавьте смены.",
                         parse_mode='Markdown', reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for shift in shifts:
        shift_text = f"{shift['start_time']}-{shift['end_time']} @{shift['username']}"
        markup.add(
            types.InlineKeyboardButton(
                f"{shift_text}",
                callback_data=f"edit_{shift['id']}"
            )
        )
    markup.add(types.InlineKeyboardButton("Назад", callback_data="back_admin"))

    text = "**Выберите смену для редактирования:**"
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    logger.info(f"Edit menu sent with {len(shifts)} shifts")


# Удалить смену
@bot.message_handler(func=lambda m: m.from_user.id in settings.ADMIN_IDS and m.text == "Удалить")
def delete_shift_menu(message):
    logger.info(f"Admin {message.from_user.id} opened delete menu")
    shifts = load_shifts()
    if not shifts:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Добавить смену")
        markup.add("График")
        markup.add("Редактировать")
        markup.add("Удалить")
        bot.send_message(message.chat.id, "**График пуст!**\nДобавьте смены.",
                         parse_mode='Markdown', reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for shift in shifts:
        shift_text = f"{shift['start_time']}-{shift['end_time']} @{shift['username']}"
        markup.add(
            types.InlineKeyboardButton(
                f"{shift_text}",
                callback_data=f"del_{shift['id']}"
            )
        )
    markup.add(types.InlineKeyboardButton("Назад", callback_data="back_admin"))

    text = "**Выберите смену для удаления:**"
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    logger.info(f"Delete menu sent with {len(shifts)} shifts")


# Обработчик INLINE кнопок
@bot.callback_query_handler(func=lambda call: call.from_user.id in settings.ADMIN_IDS)
def inline_callback_handler(call):
    data = call.data
    logger.info(f"Inline callback: {data} from user {call.from_user.id}")

    # Назад в главное меню
    if data == "back_admin":
        logger.info("Back to admin menu")
        bot.edit_message_text("**Главное меню**",
                              call.message.chat.id, call.message.message_id,
                              parse_mode='Markdown')
        admin_start(call.message)
        bot.answer_callback_query(call.id)
        return

    # Редактирование смены
    if data.startswith("edit_"):
        shift_id = int(data.split("_")[1])
        logger.info(f"Edit shift request: ID {shift_id}")

        shifts = load_shifts()
        shift = next((s for s in shifts if s["id"] == shift_id), None)

        if shift:
            user_states[call.from_user.id] = {
                "stage": "waiting_time_edit",
                "shift_id": shift_id
            }
            logger.info(f"Edit state set for shift ID {shift_id}")

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Отмена", callback_data="back_admin"))

            bot.edit_message_text(
                f"**Редактирование смены ID `{shift_id}`**\n\n"
                f"Текущее: `{shift['start_time']}-{shift['end_time']} @{shift['username']}`\n\n"
                f"**Шаг 1/2:** Введите новое время:\n"
                f"Например: `17:00-19:00`",
                call.message.chat.id, call.message.message_id,
                parse_mode='Markdown', reply_markup=markup
            )
        else:
            logger.info(f"Shift ID {shift_id} not found")
        bot.answer_callback_query(call.id)
        return

    # Удаление смены
    if data.startswith("del_"):
        shift_id = int(data.split("_")[1])
        logger.info(f"Delete shift request: ID {shift_id}")

        shifts = load_shifts()
        shift = next((s for s in shifts if s["id"] == shift_id), None)

        if shift:
            shifts = [s for s in shifts if s["id"] != shift_id]
            save_shifts(shifts)
            logger.info(f"Shift ID {shift_id} deleted: {shift['start_time']}-{shift['end_time']} @{shift['username']}")

            bot.edit_message_text(
                f"**Смена удалена!**\n\n"
                f"`{shift['start_time']}-{shift['end_time']}`: **@{shift['username']}**\n\n"
                f"ID: `{shift_id}`",
                call.message.chat.id, call.message.message_id,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id, "Смена удалена!")
        else:
            logger.info(f"Shift ID {shift_id} not found for deletion")
            bot.answer_callback_query(call.id, "Смена не найдена!")
        return

    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: m.from_user.id in settings.ADMIN_IDS)
def handle_admin_input(message):
    user_id = message.from_user.id
    text = message.text.strip()
    logger.info(f"Admin input from {user_id}: '{text}' | State: {user_states.get(user_id, 'none')}")

    # Главное меню
    if text == "Главное меню":
        logger.info(f"Admin {user_id} returned to main menu")
        admin_start(message)
        if user_id in user_states:
            del user_states[user_id]
        return

    # Отмена
    if text == "Отмена":
        logger.info(f"Admin {user_id} cancelled operation")
        if user_id in user_states:
            del user_states[user_id]
        admin_start(message)
        return

    # РЕДАКТИРОВАНИЕ: Ждём время для смены
    if user_id in user_states and user_states[user_id]["stage"] == "waiting_time_edit":
        logger.info(f"Edit time input: {text}")
        time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', text)

        if time_match:
            start_time = time_match.group(1)
            end_time = time_match.group(2)
            logger.info(f"Time validated: {start_time}-{end_time}")

            user_states[user_id] = {
                "stage": "waiting_username_edit",
                "shift_id": user_states[user_id]["shift_id"],
                "start_time": start_time,
                "end_time": end_time
            }

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add("Отмена")

            bot.send_message(message.chat.id,
                             f"**Новое время:** `{start_time}-{end_time}`\n\n"
                             "**Шаг 2/2:** Новый тег менеджера:\n"
                             "Например: `@username`",
                             parse_mode='Markdown', reply_markup=markup)
            return
        else:
            logger.info(f"Invalid time format: {text}")
            bot.send_message(message.chat.id,
                             "**Неверный формат времени!**\n"
                             "Пример: `17:00-19:00`", parse_mode='Markdown')
            return

    # РЕДАКТИРОВАНИЕ: Ждём username для смены
    elif user_id in user_states and user_states[user_id]["stage"] == "waiting_username_edit":
        logger.info(f"Edit username input: {text}")
        username_match = re.match(r'@(\w+)', text)

        if username_match:
            username = username_match.group(1)
            shift_data = user_states[user_id]
            shift_id = shift_data["shift_id"]
            logger.info(f"Username validated: @{username} for shift {shift_id}")

            # Обновляем смену
            shifts = load_shifts()
            for shift in shifts:
                if shift["id"] == shift_id:
                    shift["start_time"] = shift_data["start_time"]
                    shift["end_time"] = shift_data["end_time"]
                    shift["username"] = username
                    break

            save_shifts(shifts)
            logger.info(f"Shift {shift_id} updated: {shift_data['start_time']}-{shift_data['end_time']} @{username}")

            # Очищаем состояние
            del user_states[user_id]

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Добавить смену")
            markup.add("График")
            markup.add("Редактировать")
            markup.add("Удалить")

            bot.send_message(message.chat.id,
                             f"**Смена {shift_id} обновлена!**\n\n"
                             f"`{shift_data['start_time']}-{shift_data['end_time']}`: **@{username}**",
                             parse_mode='Markdown', reply_markup=markup)
            return
        else:
            logger.warning(f"Invalid username format: {text}")
            bot.send_message(message.chat.id,
                             "**Неверный формат!**\n"
                             "Пример: `@username`", parse_mode='Markdown')
            return

    # Этап 1: Ждём время смены (17:00-19:00)
    if user_id in user_states and user_states[user_id]["stage"] == "waiting_time":
        logger.info(f"Add time input: {text}")
        time_match = re.match(r'(\d{2}:\d{2})-(\d{2}:\d{2})', text)

        if time_match:
            start_time = time_match.group(1)
            end_time = time_match.group(2)
            logger.info(f"Add time validated: {start_time}-{end_time}")

            user_states[user_id] = {
                "stage": "waiting_username",
                "start_time": start_time,
                "end_time": end_time
            }

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add("Отмена")

            bot.send_message(message.chat.id,
                             f"**Время:** `{start_time}-{end_time}`\n\n"
                             "**Шаг 2/2:** Тег менеджера:\n"
                             "Например: `@username`",
                             parse_mode='Markdown', reply_markup=markup)
            return
        else:
            logger.warning(f"Invalid add time format: {text}")
            bot.send_message(message.chat.id,
                             "**Неверный формат времени!**\n"
                             "Пример: `17:00-19:00`", parse_mode='Markdown')
            return

    # Этап 2: Ждём username (@username)
    elif user_id in user_states and user_states[user_id]["stage"] == "waiting_username":
        logger.info(f"Add username input: {text}")
        username_match = re.match(r'@(\w+)', text)

        if username_match:
            username = username_match.group(1)
            shift_data = user_states[user_id]
            logger.info(f"Add username validated: @{username}")

            # Сохраняем смену
            shifts = load_shifts()
            new_id = max([s.get("id", 0) for s in shifts], default=0) + 1

            new_shift = {
                "id": new_id,
                "username": username,
                "start_time": shift_data["start_time"],
                "end_time": shift_data["end_time"]
            }
            shifts.append(new_shift)
            save_shifts(shifts)
            logger.info(f"New shift added: ID {new_id}, {shift_data['start_time']}-{shift_data['end_time']} @{username}")

            # Очищаем состояние
            del user_states[user_id]

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Добавить смену")
            markup.add("График")
            markup.add("Редактировать")
            markup.add("Удалить")

            bot.send_message(message.chat.id,
                             f"**Смена добавлена!**\n\n"
                             f"`{shift_data['start_time']}-{shift_data['end_time']}`: **@{username}**",
                             parse_mode='Markdown', reply_markup=markup)

            # Показываем обновлённый график
            shifts = load_shifts()
            text = "**Актуальный график:**\n\n"
            for shift in shifts:
                text += f"`{shift['start_time']}-{shift['end_time']}`: **@{shift['username']}**\n"
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
            return
        else:
            logger.warning(f"Invalid add username format: {text}")
            bot.send_message(message.chat.id,
                             "**Неверный формат!**\n"
                             "Пример: `@username`", parse_mode='Markdown')
            return


# Планировщик
def run_scheduler():
    while True:
        ping_shift_start()  # Проверяем прямо сейчас
        time.sleep(60)


# Запуск
if __name__ == "__main__":
    logger.info("Starting bot...")
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    logger.info("Bot is ready!")
    bot.infinity_polling()