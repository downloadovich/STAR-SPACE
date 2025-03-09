import sqlite3
import json

# Создаем соединение с базой данных (файл создастся автоматически)
conn = sqlite3.connect('users.db')
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

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()

# Функция для получения данных пользователя
def get_user_data(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance, referrals, used_referrals FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

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
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

# Функция для обновления данных пользователя
def update_user_data(user_id, balance=None, referrals=None, used_referrals=None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    if balance is not None:
        cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (balance, user_id))
    if referrals is not None:
        cursor.execute('UPDATE users SET referrals = ? WHERE user_id = ?', (json.dumps(referrals), user_id))
    if used_referrals is not None:
        cursor.execute('UPDATE users SET used_referrals = ? WHERE user_id = ?', (json.dumps(used_referrals), user_id))

    conn.commit()
    conn.close()

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