from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3
from datetime import datetime
import locale

# Set locale to Serbian for month names
locale.setlocale(locale.LC_TIME, "sr_RS@latin")

# Initialize bot
app = Client("zenticktickbot", api_id=27258993, api_hash="493754f4c15f9cb68d645972a2af9d53", bot_token="7608648359:AAEKTGGNGzFhXjGLOk5qu9RUuEYn8WC306w")

# Connect to SQLite database
conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

# Main menu buttons
main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("➕ Unesi trošak"), KeyboardButton("📅 Danas")],
        [KeyboardButton("🈷️ Izaberi datum"), KeyboardButton("🗓️ Ovaj mesec")]
    ],
    resize_keyboard=True
)

# Categories
categories = [
    "😋Hrana i piće", "🙀Pesak", "🐈Hrana", "🍷Izlasci", "💊Zdravlje",
    "🏫Edukacija", "✈️Putovanje", "🏠Domaćinstvo", "👕👞Odeća-obuća",
    "💅Lična nega", "🚬Cigare", "☂️Vejp", "❣️Hitni Troškovi",
    "🍺Alkohol", "🎁Pokloni"
]

# Track user conversation states
conversation_state = {}

# Start command: Show categories
@app.on_message(filters.command("start") | filters.text & filters.regex("➕ Unesi trošak"))
def start(client, message):
    # Create category buttons
    category_buttons = [[KeyboardButton(category)] for category in categories]
    
    # Reply with categories
    message.reply(
        "Izaberite kategoriju:",
        reply_markup=ReplyKeyboardMarkup(category_buttons, resize_keyboard=True)
    )
    # Update conversation state
    conversation_state[message.chat.id] = {"step": "category"}

# Handle category selection and amount entry
@app.on_message(filters.text)
def handle_category_or_amount(client, message):
    user_id = message.chat.id

    # Main menu handling
    if message.text == "📅 Danas":
        view_today(client, message)
        return
    elif message.text == "🈷️ Izaberi datum":
        pick_date(client, message)
        return
    elif message.text == "🗓️ Ovaj mesec":
        view_this_month(client, message)
        return

    # Ensure the user is in the conversation flow
    if user_id not in conversation_state:
        message.reply("Molim vas pokrenite konverzaciju pomoću /start.", reply_markup=main_menu)
        return

    state = conversation_state[user_id]

    # Step 1: Category Selection
    if state["step"] == "category":
        if message.text in categories:
            conversation_state[user_id]["category"] = message.text
            conversation_state[user_id]["step"] = "amount"
            message.reply(
                f"Odabrano: {message.text}\nUnesi cifru:"
            )
        else:
            message.reply("Izaberite važeću kategoriju sa liste ili pokrenite /start.")

    # Step 2: Amount Input
    elif state["step"] == "amount":
        if message.text.isdigit():
            amount = int(message.text)
            category = conversation_state[user_id]["category"]
            date = datetime.now().strftime("%d.%m.%Y")

            # Insert expense into the database
            cursor.execute("""
            INSERT INTO expenses (user, category, amount, date)
            VALUES (?, ?, ?, ?)
            """, ("User", category, amount, date))
            conn.commit()

            message.reply(
                f"{category}: +{amount} DIN",
                reply_markup=main_menu
            )
            # Clear the user's state after completing the action
            conversation_state.pop(user_id)
        elif message.text in categories:  # Allow changing the category
            conversation_state[user_id]["category"] = message.text
            message.reply(
                f"Odabrano: {message.text}\nUnesi cifru:"
            )
        else:
            message.reply("Unesite validan broj za iznos ili izaberite novu kategoriju.")

# Handle /danas command
def view_today(client, message):
    today = datetime.now().strftime("%d.%m.%Y")
    cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE date = ? GROUP BY category", (today,))
    data = cursor.fetchall()

    if not data:
        message.reply(f"Nema troškova za danas ({today}).", reply_markup=main_menu)
        return

    reply = "Troškovi za danas:\n"
    reply += "—————————\n"
    total = 0
    for category, amount in data:
        reply += f"{category}: {amount} DIN\n"
        total += amount
    reply += "—————————\n"
    reply += f"Ukupno: {total} DIN"

    message.reply(reply, reply_markup=main_menu)

# Handle /datum command
def pick_date(client, message):
    message.reply("Molim unesite datum u formatu DD.MM.YYYY.", reply_markup=main_menu)
    conversation_state[message.chat.id] = {"step": "date"}

@app.on_message(filters.text & filters.regex(r"^\d{2}\.\d{2}\.\d{4}$"))
def view_date(client, message):
    user_id = message.chat.id

    # Ensure the user is in the correct step
    if user_id not in conversation_state or conversation_state[user_id]["step"] != "date":
        message.reply("Molim vas pokrenite komandu 🈷️ Izaberi datum i unesite datum u ispravnom formatu.", reply_markup=main_menu)
        return

    date = message.text
    cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE date = ? GROUP BY category", (date,))
    data = cursor.fetchall()

    if not data:
        message.reply(f"Nema troškova za datum {date}.", reply_markup=main_menu)
        conversation_state.pop(user_id)
        return

    reply = f"Troškovi za {date}:\n"
    reply += "—————————\n"
    total = 0
    for category, amount in data:
        reply += f"{category}: {amount} DIN\n"
        total += amount
    reply += "—————————\n"
    reply += f"Ukupno: {total} DIN"

    message.reply(reply, reply_markup=main_menu)
    conversation_state.pop(user_id)

# Handle /ovaj_mesec command
def view_this_month(client, message):
    today = datetime.now()
    month_name = today.strftime("%B").capitalize()
    first_day = today.replace(day=1).strftime("%d.%m.%Y")
    today_str = today.strftime("%d.%m.%Y")

    cursor.execute("""
    SELECT category, SUM(amount)
    FROM expenses
    WHERE date BETWEEN ? AND ?
    GROUP BY category
    """, (first_day, today_str))
    data = cursor.fetchall()

    if not data:
        message.reply("Nema troškova za ovaj mesec.", reply_markup=main_menu)
        return

    reply = f"Troškovi za ovaj mesec {month_name}:\n"
    reply += "—————————\n"
    total = 0
    for category, amount in data:
        reply += f"{category}: {amount} DIN\n"
        total += amount
    reply += "—————————\n"
    reply += f"Ukupno: {total} DIN"

    message.reply(reply, reply_markup=main_menu)

# Run the bot
app.run()
