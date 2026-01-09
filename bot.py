import telebot
from telebot import types
import json
import os

# --- CONFIGURATION ---
BOT_TOKEN = "8472619296:AAGqtdGygSQWv3cWItNOhkFreVD29ycjgKM"
ADMIN_IDS = [5618556871, 1211251387, 542708696, 6389855906, 1804184096]
DATA_FILE = "store_memory.json"

# Clearer, more professional layout
PAYMENT_INFO = """
🌟 *C CHOIR ALBUM STORE* 🌟
━━━━━━━━━━━━━━━━━━━━
🏦 *CBE (Commercial Bank)*
└─ `1000176341606`
└─ 👤 Addisu Biru & Girma Regesa

🏦 *Cooperative Bank*
└─ `1057000131402`
└─ 👤 Gemechis Ayele & Addisu Biru
━━━━━━━━━━━━━━━━━━━━
📝 *Instructions:*
1. Transfer the total amount.
2. Take a screenshot of the receipt.
3. Send the screenshot *right here* in this chat.
"""

bot = telebot.TeleBot(BOT_TOKEN)

# --- GLOBAL DATA ---
songs = {}       
user_carts = {}  

# --- DATA PERSISTENCE ---
def load_all_data():
    global songs, user_carts
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                songs = {int(k): v for k, v in data.get('songs', {}).items()}
                user_carts = {int(k): v for k, v in data.get('user_carts', {}).items()}
        except Exception as e:
            print(f"Error loading data: {e}")

def save_all_data():
    try:
        data_to_save = {'songs': songs, 'user_carts': user_carts}
        with open(DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

load_all_data()

# --- INTERFACE HELPERS ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_numeric_price(price_str):
    try:
        return int(''.join(filter(str.isdigit, str(price_str))))
    except:
        return 0

def calculate_total(user_id):
    selected_ids = user_carts.get(user_id, [])
    return sum(get_numeric_price(songs[sid]['price']) for sid in selected_ids if sid in songs)

def get_main_keyboard(user_id):
    """Clean, simple main menu that is always accessible."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton("🎵 Browse & Select Songs"),
        types.KeyboardButton("🏠 Back to Main Menu")
    )
    if is_admin(user_id):
        markup.add(types.KeyboardButton("🛠 Admin Panel"))
    return markup

def get_song_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    selected_ids = user_carts.get(user_id, [])
    
    # Select All option
    if len(selected_ids) < len(songs) and len(songs) > 1:
        markup.add(types.InlineKeyboardButton("📥 Select All Songs", callback_data="buy_all"))
    
    for s_id, s_info in songs.items():
        status = "✅ " if s_id in selected_ids else "💿 "
        btn_text = f"{status}{s_info['title']} — {s_info['price']}"
        markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"toggle_{s_id}"))

    if selected_ids:
        total = calculate_total(user_id)
        markup.add(types.InlineKeyboardButton(text=f"💳 Checkout ({total} ETB)", callback_data="checkout"))
        markup.add(types.InlineKeyboardButton(text="🗑 Empty Cart", callback_data="clear_cart"))
    
    return markup

# --- CORE HANDLERS ---
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🏠 Back to Main Menu")
def send_welcome(message):
    welcome_text = (
        "👋 *Hello and welcome to the C CHOIR Store!*\n\n"
        "Use the buttons below to browse our album and purchase your favorite songs. "
        "The system is automatic—once your payment is verified, your songs will be delivered instantly."
    )
    bot.send_message(
        message.chat.id, welcome_text, 
        reply_markup=get_main_keyboard(message.from_user.id), 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "🎵 Browse & Select Songs")
def show_album(message):
    if not songs:
        bot.send_message(message.chat.id, "📢 No songs are currently available in the store.")
        return
    bot.send_message(
        message.chat.id, 
        "🎶 *Album Selection*\nSelect the songs you want to buy:", 
        reply_markup=get_song_markup(message.from_user.id), 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data in ["buy_all", "clear_cart", "checkout"] or call.data.startswith('toggle_'))
def handle_cart_actions(call):
    user_id = call.from_user.id
    if user_id not in user_carts: user_carts[user_id] = []

    if call.data.startswith('toggle_'):
        song_id = int(call.data.split('_')[1])
        if song_id in user_carts[user_id]:
            user_carts[user_id].remove(song_id)
        else:
            user_carts[user_id].append(song_id)
        save_all_data()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_song_markup(user_id))
    
    elif call.data == "buy_all":
        user_carts[user_id] = list(songs.keys())
        save_all_data()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_song_markup(user_id))
    
    elif call.data == "clear_cart":
        user_carts[user_id] = []
        save_all_data()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_song_markup(user_id))
    
    elif call.data == "checkout":
        total = calculate_total(user_id)
        items = "\n".join([f"• {songs[sid]['title']}" for sid in user_carts[user_id]])
        summary_text = (
            f"🛒 *Your Order Summary*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{items}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Total Amount:* `{total} ETB`\n\n"
            f"{PAYMENT_INFO}"
        )
        bot.send_message(call.message.chat.id, summary_text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
    
    bot.answer_callback_query(call.id)

# --- PAYMENT PROCESSING ---
@bot.message_handler(content_types=['photo', 'document'])
def process_payment_proof(message):
    user_id = message.from_user.id
    if not user_carts.get(user_id):
        bot.reply_to(message, "❌ Your cart is empty. Please select songs before sending payment proof.")
        return
    
    total = calculate_total(user_id)
    cart_data = ",".join(map(str, user_carts[user_id]))
    
    # Notify Admin
    for admin_id in ADMIN_IDS:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Approve Payment", callback_data=f"apprv_{user_id}_{cart_data}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"rjct_{user_id}")
        )
        
        admin_notif = (
            f"📥 *New Purchase Request*\n\n"
            f"👤 *Customer:* {message.from_user.first_name} (@{message.from_user.username})\n"
            f"💰 *Total:* `{total} ETB`"
        )
        if message.content_type == 'photo':
            bot.send_photo(admin_id, message.photo[-1].file_id, caption=admin_notif, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_document(admin_id, message.document.file_id, caption=admin_notif, reply_markup=markup, parse_mode="Markdown")
    
    bot.reply_to(message, "⏳ *Thank you!* Your payment proof has been sent to our team for verification.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('apprv_', 'rjct_')))
def admin_approval_logic(call):
    parts = call.data.split('_')
    action, customer_id = parts[0], int(parts[1])

    if action == "apprv":
        song_ids = map(int, parts[2].split(','))
        bot.send_message(customer_id, "🎉 *Payment Verified!*\nYour songs are being delivered below. Enjoy!")
        
        for sid in song_ids:
            if sid in songs:
                s = songs[sid]
                # Dynamic delivery logic based on file type
                delivery_func = getattr(bot, f"send_{s['file_type']}")
                delivery_func(customer_id, s['file_id'], caption=f"🎶 {s['title']}")
        
        user_carts[customer_id] = []
        save_all_data()
        bot.edit_message_caption("✅ *Approved and Delivered*", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(customer_id, "❌ *Payment Verification Failed.*\nYour receipt was not accepted. Please contact support if you believe this is an error.")
        bot.edit_message_caption("❌ *Payment Rejected*", call.message.chat.id, call.message.message_id)

# --- ADMIN PANEL ---
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def show_admin_panel(message):
    if not is_admin(message.from_user.id): return
    if not songs:
        bot.send_message(message.chat.id, "The store database is empty.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for s_id, s_info in songs.items():
        markup.add(
            types.InlineKeyboardButton(f"✏️ Edit: {s_info['title']}", callback_data=f"adm_edit_{s_id}"),
            types.InlineKeyboardButton(f"🗑 Delete", callback_data=f"adm_del_{s_id}")
        )
    bot.send_message(message.chat.id, "🛠 *Store Inventory Manager*", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_'))
def handle_admin_tools(call):
    if not is_admin(call.from_user.id): return
    action_data = call.data.split('_')
    action, s_id = action_data[1], int(action_data[2])

    if action == "del":
        if s_id in songs:
            del songs[s_id]
            save_all_data()
            bot.answer_callback_query(call.id, "Song removed from store.")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_admin_panel(call.message)

    elif action == "edit":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Change Title", callback_data=f"upd_title_{s_id}"),
            types.InlineKeyboardButton("Change Price", callback_data=f"upd_price_{s_id}")
        )
        bot.edit_message_text(f"Editing: *{songs[s_id]['title']}*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['audio', 'document', 'video', 'voice'])
def handle_admin_upload(message):
    if not is_admin(message.from_user.id): return
    file_type = message.content_type
    file_id = getattr(message, file_type).file_id if file_type != 'photo' else message.photo[-1].file_id
    
    msg = bot.reply_to(message, "✨ *New Song Detected!*\nPlease enter the *Song Title*:")
    bot.register_next_step_handler(msg, lambda m: process_new_upload(m, file_id, file_type))

def process_new_upload(message, file_id, file_type):
    title = message.text
    msg = bot.reply_to(message, f"💰 Enter the price for *{title}* (numbers only):")
    bot.register_next_step_handler(msg, lambda m: finalize_upload(m, file_id, file_type, title))

def finalize_upload(message, file_id, file_type, title):
    new_id = max(songs.keys() or [0]) + 1
    songs[new_id] = {
        'title': title, 
        'price': f"{message.text} ETB", 
        'file_id': file_id, 
        'file_type': file_type
    }
    save_all_data()
    bot.reply_to(message, f"✅ *Successfully added:* {title}", reply_markup=get_main_keyboard(message.from_user.id), parse_mode="Markdown")

print("C CHOIR Store Bot is active...")
bot.infinity_polling()
