import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest
from dotenv import load_dotenv
import os
import pytz
from datetime import time
import sqlite3
import json
import atexit

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем, что токен загружен
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден. Укажите его в файле .env")

# Укажите имя вашего бота (без @)
BOT_USERNAME = "Stars_Space_bot"

# Укажите ваш CHAT_ID
CHAT_ID = 7524255042

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Укажите chat_id вашего канала
CHANNEL_CHAT_ID = "-1002451778906"  # Замените на chat_id вашего канала
CHANNEL_USERNAME = "@STAR_SPAIS"

# Дополнительные каналы для подписки
ADDITIONAL_CHANNELS = [
    {"username": "@moneyobus", "chat_id": " -1002302071983"},  # Замените на данные первого канала
    {"username": "@kamysn_mlem", "chat_id": " -1002480312005"},  # Замените на данные второго канала
    {"username": "@blacklistLoadovicha", "chat_id": " -1002492802980"},  # Замените на данные третьего канала
]

# Создаем соединение с базой данных (файл создастся автоматически)
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

# Создаем таблицу для хранения данных пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referrals TEXT DEFAULT '[]',
    used_referrals TEXT DEFAULT '[]'
)
''')
conn.commit()

# Функция для получения данных пользователя
def get_user_data(user_id):
    cursor.execute('SELECT balance, referrals, used_referrals FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        balance, referrals, used_referrals = result
        return {
            "balance": balance,
            "referrals": json.loads(referrals),
            "used_referrals": json.loads(used_referrals)
        }
    else:
        return None

# Функция для создания нового пользователя
def create_user(user_id):
    cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()

# Функция для обновления данных пользователя
def update_user_data(user_id, balance=None, referrals=None, used_referrals=None):
    if balance is not None:
        cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (balance, user_id))
    if referrals is not None:
        cursor.execute('UPDATE users SET referrals = ? WHERE user_id = ?', (json.dumps(referrals), user_id))
    if used_referrals is not None:
        cursor.execute('UPDATE users SET used_referrals = ? WHERE user_id = ?', (json.dumps(used_referrals), user_id))
    conn.commit()

# Функция для добавления реферала
def add_referral(user_id, referral_id):
    user_data = get_user_data(user_id)
    if user_data:
        referrals = user_data["referrals"]
        used_referrals = user_data["used_referrals"]

        if referral_id not in used_referrals:
            referrals.append(referral_id)
            used_referrals.append(referral_id)
            update_user_data(user_id, referrals=referrals, used_referrals=used_referrals)

# Функция для пополнения баланса
def add_balance(user_id, amount):
    user_data = get_user_data(user_id)
    if user_data:
        new_balance = user_data["balance"] + amount
        update_user_data(user_id, balance=new_balance)

# Функция проверки подписки на все каналы
async def is_subscribed(update: Update, context: CallbackContext) -> bool:
    user_id = update.effective_user.id
    try:
        # Проверяем подписку на основной канал
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if chat_member.status not in ["member", "administrator", "creator"]:
            return False

        # Проверяем подписку на дополнительные каналы
        for channel in ADDITIONAL_CHANNELS:
            chat_member = await context.bot.get_chat_member(chat_id=channel["username"], user_id=user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False

        return True
    except BadRequest:
        return False

# Обработчик команды /start
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # Получаем данные пользователя из базы данных
    user_data = get_user_data(user_id)

    # Если пользователя нет в базе данных, создаем его
    if not user_data:
        create_user(user_id)
        user_data = get_user_data(user_id)

    # Обработка реферальной ссылки
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if referrer_id != user_id and get_user_data(referrer_id):
            # Получаем данные реферера
            referrer_data = get_user_data(referrer_id)

            # Проверяем, не использовал ли уже пользователь эту реферальную ссылку
            if user_id not in referrer_data["used_referrals"]:
                # Проверяем, подписан ли пользователь на все каналы
                if await is_subscribed(update, context):
                    # Пополняем баланс реферера на 2 звезды
                    add_balance(referrer_id, 2)
                    add_referral(referrer_id, user_id)

                    # Отправляем сообщение рефереру
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text="🎉 По вашей ссылке перешли и подписались на канал! Вы получили 2 звезды.",
                    )
                else:
                    # Пользователь не подписан на все каналы
                    logger.info(f"Пользователь {user_id} перешел по ссылке, но не подписан на все каналы.")
            else:
                # Пользователь уже использовал эту ссылку
                logger.info(f"Пользователь {user_id} уже использовал ссылку реферера {referrer_id}.")

    # Проверяем, подписан ли пользователь на все каналы
    if await is_subscribed(update, context):
        # Если подписан, показываем меню с балансом и реферальной ссылкой
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"  # Реферальная ссылка

        # Создаем клавиатуру с кнопками
        keyboard = [
            [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="show_ref_link")],
            [InlineKeyboardButton("Вывод", callback_data="withdraw")],
            [InlineKeyboardButton("Мои рефералы", callback_data="referrals")],
            [InlineKeyboardButton("Информация", callback_data="info")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем текстовое сообщение с кнопками
        await update.message.reply_text(
            f"🎉 Вы уже подписаны на все каналы!\n\n"
            f"⭐ Ваш баланс: {user_data['balance']} звезд",
            reply_markup=reply_markup,
        )
    else:
        # Если не подписан, показываем кнопки для подписки
        keyboard = [
            [InlineKeyboardButton("Подписаться на основной канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("Подписаться на канал 1", url=f"https://t.me/{ADDITIONAL_CHANNELS[0]['username'][1:]}")],
            [InlineKeyboardButton("Подписаться на канал 2", url=f"https://t.me/{ADDITIONAL_CHANNELS[1]['username'][1:]}")],
            [InlineKeyboardButton("Подписаться на канал 3", url=f"https://t.me/{ADDITIONAL_CHANNELS[2]['username'][1:]}")],
            [InlineKeyboardButton("Проверить", callback_data="check_subscription")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Привет! Подпишись на все каналы и нажми 'Проверить', чтобы продолжить.",
            reply_markup=reply_markup,
        )

# Обработчик команды /add_balance
async def add_balance_command(update: Update, context: CallbackContext) -> None:
    # Проверяем, что команда вызвана администратором
    if update.effective_user.id != 1855791379:  # Замените на ваш chat_id
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return

    # Проверяем, что переданы два аргумента: ID пользователя и количество звезд
    if len(context.args) != 2:
        await update.message.reply_text("❌ Используйте команду так: /add_balance <user_id> <amount>")
        return

    user_id, amount = context.args

    # Проверяем, что user_id и amount — числа
    if not user_id.isdigit() or not amount.isdigit():
        await update.message.reply_text("❌ ID пользователя и количество звезд должны быть числами.")
        return

    user_id = int(user_id)
    amount = int(amount)

    # Пополняем баланс
    add_balance(user_id, amount)

    # Отправляем сообщение об успешном пополнении
    await update.message.reply_text(f"✅ Баланс пользователя {user_id} пополнен на {amount} звезд. Новый баланс: {get_user_data(user_id)['balance']}.")

# Обработчик кнопки "Проверить"
async def check_subscription(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if await is_subscribed(update, context):
        user_id = query.from_user.id
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"  # Реферальная ссылка

        # Создаем клавиатуру с кнопками
        keyboard = [
            [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="show_ref_link")],
            [InlineKeyboardButton("Вывод", callback_data="withdraw")],
            [InlineKeyboardButton("Мои рефералы", callback_data="referrals")],
            [InlineKeyboardButton("Информация", callback_data="info")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"🎉 Вы подписаны на все каналы!\n\n"
            f"⭐ Ваш баланс: {get_user_data(user_id)['balance']} звезд",
            reply_markup=reply_markup,
        )
    else:
        await query.edit_message_text("❌ Вы не подписаны на все каналы. Пожалуйста, подпишитесь и нажмите 'Проверить' снова.")

# Обработчик кнопки "🔗 Реферальная ссылка"
async def show_ref_link(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"  # Реферальная ссылка

    # Создаем клавиатуру с кнопкой "Вернуться"
    keyboard = [
        [InlineKeyboardButton("Вернуться", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Редактируем сообщение с текстом реферальной ссылки и кнопкой "Вернуться"
    await query.edit_message_text(
        f"🔗 Ваша реферальная ссылка:\n\n{ref_link}",
        reply_markup=reply_markup,
    )

# Обработчик кнопки "Мои рефералы"
async def show_referrals(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    referrals = user_data["referrals"] if user_data else []

    if referrals:
        # Собираем информацию о рефералах
        referral_list = []
        for referral_id in referrals:
            try:
                # Получаем информацию о пользователе
                user = await context.bot.get_chat(referral_id)
                username = user.username if user.username else user.first_name
                referral_list.append(f"@{username}" if user.username else username)
            except Exception:
                referral_list.append(f"Пользователь {referral_id}")

        text = "Ваши рефералы:\n" + "\n".join(referral_list)
    else:
        text = "У вас пока нет рефералов."

    # Добавляем кнопку "Вернуться"
    keyboard = [
        [InlineKeyboardButton("Вернуться", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup)

# Обработчик кнопки "Информация"
async def show_info(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Добавляем кнопку "Вернуться"
    keyboard = [
        [InlineKeyboardButton("Вернуться", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "ℹ️ Информация о боте:\n\n"
        "Этот бот позволяет вам зарабатывать звезды, приглашая друзей.\n"
        "За каждого друга, который подпишется на канал по вашей ссылке, вы получите 2 звезды.\n\n"
        "Связано с нами💫 : телеграм канал со всеми актуальными новостями : https://t.me/STAR_SPAIS ‼️.\n\n"
        "Канал с выплатами 🌟 пользователям : https://t.me/lilviplata ‼️.\n",
        reply_markup=reply_markup,
    )

# Обработчик кнопки "Вывод"
async def withdraw(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Проверяем, подписан ли пользователь на все каналы
    if not await is_subscribed(update, context):
        # Если не подписан, показываем сообщение с предложением подписаться
        keyboard = [
            [InlineKeyboardButton("Подписаться на основной канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("Подписаться на канал 1", url=f"https://t.me/{ADDITIONAL_CHANNELS[0]['username'][1:]}")],
            [InlineKeyboardButton("Подписаться на канал 2", url=f"https://t.me/{ADDITIONAL_CHANNELS[1]['username'][1:]}")],
            [InlineKeyboardButton("Подписаться на канал 3", url=f"https://t.me/{ADDITIONAL_CHANNELS[2]['username'][1:]}")],
            [InlineKeyboardButton("Проверить", callback_data="check_subscription")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "❌ Вы не подписаны на все каналы. Пожалуйста, подпишитесь и нажмите 'Проверить', чтобы продолжить.",
            reply_markup=reply_markup,
        )
        return

    # Если подписан, показываем меню вывода
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    balance = user_data["balance"] if user_data else 0

    # Создаем клавиатуру с кнопками "15", "25", "50", "100" и "Вернуться"
    keyboard = [
        [InlineKeyboardButton("15", callback_data="withdraw_15")],
        [InlineKeyboardButton("25", callback_data="withdraw_25")],
        [InlineKeyboardButton("50", callback_data="withdraw_50")],
        [InlineKeyboardButton("100", callback_data="withdraw_100")],
        [InlineKeyboardButton("Вернуться", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"⭐ Ваш баланс: {balance} звезд\n\n"
        "Выберите количество звезд для вывода:",
        reply_markup=reply_markup,
    )

# Обработчик кнопки "15"
async def withdraw_15(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Устанавливаем количество звезд для списания
    context.user_data["withdraw_amount"] = 15

    # Запрашиваем ID у пользователя
    await query.edit_message_text("Введите свой ID:")

    # Сохраняем состояние, чтобы обработать следующий ввод пользователя
    context.user_data["awaiting_id"] = True

# Обработчик кнопки "25"
async def withdraw_25(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Устанавливаем количество звезд для списания
    context.user_data["withdraw_amount"] = 25

    # Запрашиваем ID у пользователя
    await query.edit_message_text("Введите свой ID:")

    # Сохраняем состояние, чтобы обработать следующий ввод пользователя
    context.user_data["awaiting_id"] = True

# Обработчик кнопки "50"
async def withdraw_50(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Устанавливаем количество звезд для списания
    context.user_data["withdraw_amount"] = 50

    # Запрашиваем ID у пользователя
    await query.edit_message_text("Введите свой ID:")

    # Сохраняем состояние, чтобы обработать следующий ввод пользователя
    context.user_data["awaiting_id"] = True

# Обработчик кнопки "100"
async def withdraw_100(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Устанавливаем количество звезд для списания
    context.user_data["withdraw_amount"] = 100

    # Запрашиваем ID у пользователя
    await query.edit_message_text("Введите свой ID:")

    # Сохраняем состояние, чтобы обработать следующий ввод пользователя
    context.user_data["awaiting_id"] = True

# Обработчик ввода ID
async def handle_id_input(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_input = update.message.text

    if context.user_data.get("awaiting_id"):
        # Сохраняем введенный ID
        context.user_data["entered_id"] = user_input

        # Получаем количество звезд для списания
        withdraw_amount = context.user_data.get("withdraw_amount", 0)

        # Создаем клавиатуру с кнопками "Подтвердить" и "Отмена"
        keyboard = [
            [InlineKeyboardButton("Подтвердить", callback_data="confirm_withdraw")],
            [InlineKeyboardButton("Отмена", callback_data="cancel_withdraw")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Вы ввели ID: {user_input}\n\nПодтвердите вывод {withdraw_amount} звезд:",
            reply_markup=reply_markup,
        )

        # Сбрасываем состояние ожидания ID
        context.user_data["awaiting_id"] = False

# Обработчик кнопки "Отмена"
async def cancel_withdraw(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Возвращаем пользователя в раздел вывода
    await withdraw(update, context)

# Обработчик кнопки "Подтвердить"
async def confirm_withdraw(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    entered_id = context.user_data.get("entered_id")
    withdraw_amount = context.user_data.get("withdraw_amount", 0)

    if entered_id:
        # Проверяем, достаточно ли звезд на балансе
        user_data = get_user_data(user_id)
        if user_data and user_data["balance"] >= withdraw_amount:
            # Списываем звезды
            new_balance = user_data["balance"] - withdraw_amount
            update_user_data(user_id, balance=new_balance)

            # Отправляем ID в канал
            await context.bot.send_message(
                chat_id=CHANNEL_CHAT_ID,
                text=f"Новый вывод! ID пользователя: {entered_id}, списано {withdraw_amount} звезд.",
            )

            # Возвращаем пользователя в главное меню
            await back_to_menu(update, context)
        else:
            # Сообщение о недостатке звезд с кнопкой "Вернуться"
            keyboard = [
                [InlineKeyboardButton("Вернуться", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"❌ Недостаточно звезд на балансе. Требуется {withdraw_amount}, а у вас {user_data['balance'] if user_data else 0}.",
                reply_markup=reply_markup,
            )
    else:
        await query.edit_message_text("❌ Ошибка: ID не найден.")

# Обработчик кнопки "Вернуться"
async def back_to_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"  # Реферальная ссылка

    # Создаем клавиатуру с кнопками
    keyboard = [
        [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="show_ref_link")],
        [InlineKeyboardButton("Вывод", callback_data="withdraw")],
        [InlineKeyboardButton("Мои рефералы", callback_data="referrals")],
        [InlineKeyboardButton("Информация", callback_data="info")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Редактируем сообщение с текстом и кнопками
    await query.edit_message_text(
        f"🎉 Вы уже подписаны на все каналы!\n\n"
        f"⭐ Ваш баланс: {get_user_data(user_id)['balance']} звезд",
        reply_markup=reply_markup,
    )

# Основная функция запуска бота
def main() -> None:
    # Укажите временную зону
    timezone = pytz.timezone("Europe/Moscow")

    # Создайте Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_balance", add_balance_command))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))
    application.add_handler(CallbackQueryHandler(show_ref_link, pattern="^show_ref_link$"))
    application.add_handler(CallbackQueryHandler(show_referrals, pattern="^referrals$"))
    application.add_handler(CallbackQueryHandler(show_info, pattern="^info$"))
    application.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(withdraw_15, pattern="^withdraw_15$"))
    application.add_handler(CallbackQueryHandler(withdraw_25, pattern="^withdraw_25$"))
    application.add_handler(CallbackQueryHandler(withdraw_50, pattern="^withdraw_50$"))
    application.add_handler(CallbackQueryHandler(withdraw_100, pattern="^withdraw_100$"))
    application.add_handler(CallbackQueryHandler(confirm_withdraw, pattern="^confirm_withdraw$"))
    application.add_handler(CallbackQueryHandler(cancel_withdraw, pattern="^cancel_withdraw$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_id_input))

    # Добавляем задачу в JobQueue (пример)
    application.job_queue.run_daily(callback=daily_task, time=time(12, 0, tzinfo=timezone))

    # Запускаем бота
    application.run_polling()

# Функция, которая будет выполняться ежедневно
async def daily_task(context: CallbackContext):
    await context.bot.send_message(chat_id=CHAT_ID, text="Это ежедневное сообщение!")

# Закрываем соединение с базой данных при завершении работы
def close_db_connection():
    conn.close()

atexit.register(close_db_connection)

if __name__ == "__main__":
    main()
