import telebot
from telebot import types
import sqlite3
import datetime
import random

# === Configuration ===
TOKEN = 'YOUR_TOKEN_HERE'
ADMIN_IDS = [123456789]  # Replace with your admin IDs
BOT_LINK = 'https://t.me/your_bot_username'

bot = telebot.TeleBot(TOKEN)

# === Emoji Buttons ===
EMOJI_BUTTONS = {
    'Dolphin': '🐬',
    'Robot':    '🤖',
    'Sun':      '☀',
    'Heart':    '❤',
    'Poop':     '💩',
    'Brain':    '🧠',
    'Ghost':    '👻',
    'Pumpkin':  '🎃',
    'Panda':    '🐼',
}

# === Database Setup ===
DB_PATH = 'users.db'

def init_db():
    # Initialize the database and create the users table if not exists
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                registration TEXT,
                blocked INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 0
            )
        ''')

init_db()

# === Database Helper Functions ===
def get_user(user_id):
    # Retrieve a user record by user_id
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, registration, blocked, attempts FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()

def add_user(user_id, username):
    # Add or replace a user, resetting blocked status and attempts
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (id, username, registration, blocked, attempts)
            VALUES (?, ?, ?, 0, 0)
        ''', (user_id, username, now))

def update_attempt(user_id, username=None, success=False):
    """
    Update the attempt counter for a user.
    - If success=True, reset attempts to 0.
    - Otherwise, increment attempts; block user if attempts >= 3.
    If the user does not exist, create a new record (if username provided).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT attempts, blocked FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()

        if row is None:
            # New user: initialize record
            attempts, blocked = 0, 0
            if username is None:
                username = 'unknown'
            reg_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO users (id, username, registration, blocked, attempts)
                VALUES (?, ?, ?, 0, 0)
            ''', (user_id, username, reg_time))
        else:
            attempts, blocked = row

        if success:
            # Reset attempts on successful verification
            cursor.execute('UPDATE users SET attempts = 0 WHERE id = ?', (user_id,))
        else:
            # Increment attempts and block if necessary
            attempts += 1
            cursor.execute('UPDATE users SET attempts = ? WHERE id = ?', (attempts, user_id))
            if attempts >= 3 and not blocked:
                cursor.execute('UPDATE users SET blocked = 1 WHERE id = ?', (user_id,))

def is_blocked(user_id):
    # Check if a user is blocked
    user = get_user(user_id)
    return bool(user and user[3])

def get_all_users():
    # Return a list of all users with their status
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, registration, blocked FROM users')
        return cursor.fetchall()

# === Bot Logic ===

def send_captcha(chat_id, user_id, username):
    # Send an emoji CAPTCHA to the user
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    target_key = random.choice(list(EMOJI_BUTTONS.keys()))
    target_emoji = EMOJI_BUTTONS[target_key]

    buttons = []
    for name, emoji in EMOJI_BUTTONS.items():
        data = f'captcha_{target_emoji}_{emoji}_{user_id}_{username}'
        buttons.append(types.InlineKeyboardButton(text=emoji, callback_data=data))

    for i in range(0, len(buttons), 3):
        keyboard.add(*buttons[i:i+3])

    bot.send_message(
        chat_id,
        f"🔒 Verification required!\nPlease click on the emoji for *{target_key}*",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['start'])
def handle_start(message):
    # Handle the /start command
    if message.chat.type != 'private':
        # Prompt user to switch to private chat
        bot.send_message(
            message.chat.id,
            '❗ Please message me in private.',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton('Go to bot', url=BOT_LINK)
            )
        )
        return

    uid = message.from_user.id
    user = get_user(uid)
    if user:
        if is_blocked(uid):
            bot.send_message(message.chat.id, '🚫 You are blocked due to too many failed attempts.')
        else:
            bot.send_message(message.chat.id, '✅ You are already registered.')
    else:
        # Start CAPTCHA verification
        send_captcha(message.chat.id, uid, message.from_user.username or 'unknown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('captcha_'))
def handle_captcha(call):
    # Handle CAPTCHA button presses
    _, correct, chosen, uid_str, username = call.data.split('_', 4)
    uid = int(uid_str)

    if is_blocked(uid):
        bot.answer_callback_query(call.id, '🚫 You are blocked.')
        return

    if correct == chosen:
        # Successful verification
        add_user(uid, username)
        bot.answer_callback_query(call.id, '✅ Verification successful!')
        bot.send_message(call.message.chat.id, '🎉 You have been registered.')
    else:
        # Failed verification
        update_attempt(uid, username=username, success=False)
        if is_blocked(uid):
            bot.answer_callback_query(call.id, '🚫 Too many failed attempts. You are blocked.')
            bot.send_message(call.message.chat.id, '🚫 You have been blocked.')
        else:
            bot.answer_callback_query(call.id, '❌ Incorrect. Try again.')
            send_captcha(call.message.chat.id, uid, username)

@bot.message_handler(commands=['list'])
def handle_list(message):
    # Handle the /list command for admins
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, '❌ You are not authorized.')
        return

    users = get_all_users()
    if not users:
        bot.send_message(message.chat.id, 'ℹ️ No users found.')
        return

    text = '<b>Registered Users:</b>\n\n'
    for uid, uname, reg, blocked in users:
        status = '🔴 Blocked' if blocked else '🟢 Active'
        text += f'🆔 <code>{uid}</code>\n👤 @{uname}\n📅 {reg}\n{status}\n\n'
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda m: True)
def fallback(message):
    # Fallback for unrecognized messages
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, 'Use /start to register or /list if you\'re an admin.')

# === Start Bot ===
if __name__ == '__main__':
    print('🤖 Bot is running...')
    bot.polling(none_stop=True, interval=0.25)
