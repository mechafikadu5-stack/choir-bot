import telebot
from telebot import types

# --- CONFIGURATION ---
BOT_TOKEN = "8472619296:AAGqtdGygSQWv3cWItNOhkFreVD29ycjgKM"
ADMIN_IDS = [5618556871,1211251387,542708696,6389855906,1804184096]

# Personalized payment info for choir album
PAYMENT_INFO = """
💳 *Payment Methods for C CHOIR Album*
-----------------------
🏦 CBE (Commercial Bank of Ethiopia): 
`1000176341606`
👤 Name: Addisu Biru & Girma Regesa
🏦 Cooperative Bank:
`1057000131402`
👤 Name: Gemechis Ayele & Addisu Biru

📱 Telebirr: 
`09xxxxxx`
👤 Name: Mecha
-----------------------
📸 Please send a screenshot of your payment after transferring.
"""

bot = telebot.TeleBot(BOT_TOKEN)

# --- IN-MEMORY DATA STORAGE ---
songs = {}  # { id: { 'title', 'price', 'file_id', 'file_type' } }
song_counter = 1
pending_orders = {}  # { user_id: { 'song_id' } }

# --- HELPER FUNCTIONS ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- ADMIN UPLOAD LOGIC ---
@bot.message_handler(content_types=['audio', 'document', 'video', 'voice'])
def handle_admin_upload(message):
    if not is_admin(message.from_user.id):
        return

    file_id = ""
    file_type = message.content_type

    if file_type == 'audio':
        file_id = message.audio.file_id
    elif file_type == 'document':
        file_id = message.document.file_id
    elif file_type == 'video':
        file_id = message.video.file_id
    elif file_type == 'voice':
        file_id = message.voice.file_id

    msg = bot.reply_to(message, "📂 File received! Please enter the *Song Title* for the album:")
    bot.register_next_step_handler(msg, process_title, file_id, file_type)

def process_title(message, file_id, file_type):
    title = message.text
    if not title:
        msg = bot.reply_to(message, "❌ Invalid title. Enter the song title:")
        bot.register_next_step_handler(msg, process_title, file_id, file_type)
        return

    msg = bot.reply_to(message, f"💰 Enter the price for '{title}':")
    bot.register_next_step_handler(msg, process_price, file_id, file_type, title)

def process_price(message, file_id, file_type, title):
    price = message.text
    global song_counter

    songs[song_counter] = {
        'title': title,
        'price': price,
        'file_id': file_id,
        'file_type': file_type
    }

    bot.reply_to(
        message,
        f"✅ Song added to the C CHOIR album!\n🎵 *{title}*\n💰 Price: {price}\nItem #{song_counter}",
        parse_mode="Markdown"
    )
    song_counter += 1

# --- USER COMMANDS & BROWSING ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Welcome to the *C CHOIR Album Store*!\n\n"
        "🎶 Explore our choir songs from *Waldaa Adventistii Guyyaa Torbaffaa* below:"
    )

    if not songs:
        bot.send_message(message.chat.id, "🛒 The album is currently empty. Check back later!")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for s_id, s_info in songs.items():
        btn = types.InlineKeyboardButton(
            text=f"🎵 {s_info['title']} - {s_info['price']}",
            callback_data=f"buy_{s_id}"
        )
        markup.add(btn)

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- BUYING FLOW ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy_request(call):
    song_id = int(call.data.split('_')[1])
    user_id = call.from_user.id

    if song_id not in songs:
        bot.answer_callback_query(call.id, "❌ Song not available.")
        return

    pending_orders[user_id] = {'song_id': song_id}

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=(
            f"🎵 Selected: *{songs[song_id]['title']}*\n"
            f"💰 Price: *{songs[song_id]['price']}*\n\n"
            f"{PAYMENT_INFO}\n"
            "📸 *Please upload your payment screenshot now.*"
        ),
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=['photo', 'document'])
def handle_payment_screenshot(message):
    user_id = message.from_user.id

    if user_id not in pending_orders:
        return

    if message.content_type == 'document':
        if not (message.document.mime_type and message.document.mime_type.startswith('image/')):
            bot.reply_to(message, "❌ Please send a photo or image document as payment proof.")
            return

    song_id = pending_orders[user_id]['song_id']
    song_title = songs[song_id]['title']

    bot.reply_to(message, "⏳ Payment proof received! Admin will verify shortly.")

    for admin_id in ADMIN_IDS:
        markup = types.InlineKeyboardMarkup()
        approve_btn = types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{song_id}")
        reject_btn = types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        markup.add(approve_btn, reject_btn)

        caption = (
            f"🚨 *New Payment Proof*\n"
            f"User: {message.from_user.first_name}\n"
            f"Song: {song_title}\n"
            f"Price: {songs[song_id]['price']}"
        )

        if message.content_type == 'photo':
            bot.send_photo(admin_id, message.photo[-1].file_id, caption=caption, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_document(admin_id, message.document.file_id, caption=caption, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN APPROVAL ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def handle_admin_decision(call):
    if not is_admin(call.from_user.id):
        return

    data = call.data.split('_', maxsplit=2)
    action = data[0]
    target_user_id = int(data[1])

    if action == "approve":
        song_id = int(data[2])
        song = songs.get(song_id)
        if not song:
            bot.answer_callback_query(call.id, "❌ Error: Song data lost.")
            return

        try:
            bot.send_message(target_user_id, f"✅ Payment approved! Enjoy your song: *{song['title']}*", parse_mode="Markdown")

            if song['file_type'] == 'audio':
                bot.send_audio(target_user_id, song['file_id'], caption=f"🎶 {song['title']}")
            elif song['file_type'] == 'voice':
                bot.send_voice(target_user_id, song['file_id'], caption=f"🎶 {song['title']}")
            elif song['file_type'] == 'video':
                bot.send_video(target_user_id, song['file_id'], caption=f"🎶 {song['title']}")
            else:
                bot.send_document(target_user_id, song['file_id'], caption=f"🎶 {song['title']}")

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="✅ Approved & Delivered",
                reply_markup=None
            )

            pending_orders.pop(target_user_id, None)

        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Delivery failed: {str(e)}")

    elif action == "reject":
        bot.send_message(target_user_id, "❌ Your payment was rejected. Please contact the admin for support.")
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="❌ Rejected",
            reply_markup=None
        )
        pending_orders.pop(target_user_id, None)

# --- RUN BOT ---
print("🎵 C CHOIR Album Bot is running...")
bot.infinity_polling()

