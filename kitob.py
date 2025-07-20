from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import os
import re
import time
from collections import defaultdict, Counter

API_TOKEN = '7517182492:AAGT9_mqt44oxFCeouIeSgUjLsJZFUTuO_Q'
CHANNEL_CHAT_ID = "@AllBooksHub_uz"
ADMIN_PHONE = '947730302'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

search_mode_users = set()
audio_search_mode_users = set()
genre_search_mode = defaultdict(str)
last_active = defaultdict(lambda: 0)
user_phone_map = dict()
search_stats = Counter()
user_limits = defaultdict(lambda: {'book': 0, 'audio': 0})
user_messages = defaultdict(list)
all_users = set()

KITOBLAR_PAPKA = "kitoblar"
AUDIO_PAPKA = "audio"
KANAL_USERNAME = "@AllBooksHub_uz"
DAILY_LIMIT = 1000

main_menu = InlineKeyboardMarkup(row_width=1)
main_menu.add(
    InlineKeyboardButton("📚 Kitob qidirish", callback_data="search"),
    InlineKeyboardButton("🎧 Audio kitob qidirish", callback_data="search_audio"),
    InlineKeyboardButton("🧹 Chatni tozalash", callback_data="clear_chat"),
    InlineKeyboardButton("📩 Murojaat", callback_data="contact"),
    InlineKeyboardButton("👨‍💻 Admin paneli", callback_data="admin_panel")
)

confirm_menu = InlineKeyboardMarkup(row_width=2)
confirm_menu.add(
    InlineKeyboardButton("✅ Ha, tozalash", callback_data="confirm_clear"),
    InlineKeyboardButton("❌ Yo‘q, orqaga", callback_data="back")
)

genre_menu = InlineKeyboardMarkup(row_width=1)
for genre in ["biznes", "ertak", "jahon adabiyoti", "o'zbek adabiyoti"]:
    genre_menu.add(InlineKeyboardButton(genre.title(), callback_data=f"genre_{genre}"))
genre_menu.add(InlineKeyboardButton("⬅️ Orqaga", callback_data="back"))

back_menu = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Orqaga", callback_data="back"))

def normalize(text):
    return re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ ]", "", text.lower()).strip()

async def check_user_in_channel(user_id):
    try:
        member = await bot.get_chat_member(KANAL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def channel_prompt():
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔗 Kanalga obuna bo‘lish", url=f"https://t.me/{KANAL_USERNAME[1:]}") ,
        InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")
    )

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    all_users.add(message.from_user.id)

    if message.from_user.id not in user_phone_map:
        contact_btn = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        contact_btn.add(KeyboardButton("📞 Raqamni ulashish", request_contact=True))
        await message.answer("Iltimos, telefon raqamingizni ulashing:", reply_markup=contact_btn)
        return

    if not await check_user_in_channel(message.from_user.id):
        await message.answer("❌ Iltimos, botdan foydalanish uchun kanalga obuna bo‘ling!", reply_markup=channel_prompt())
        return

    await message.answer("Asosiy menyu:", reply_markup=main_menu)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def contact_handler(message: types.Message):
    user_phone_map[message.from_user.id] = message.contact.phone_number[-9:]
    await message.answer("✅ Raqam qabul qilindi!", reply_markup=ReplyKeyboardRemove())
    await start_handler(message)

@dp.callback_query_handler(lambda c: True)
async def callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    last_active[user_id] = time.time()
    all_users.add(user_id)

    if not await check_user_in_channel(user_id):
        await callback_query.message.edit_text("❌ Kanalga obuna bo‘ling!", reply_markup=channel_prompt())
        return

    data = callback_query.data

    if data == 'check_sub':
        if await check_user_in_channel(user_id):
            await callback_query.message.edit_text("Asosiy menyu:", reply_markup=main_menu)
        else:
            await callback_query.answer("Hali obuna bo‘lmagansiz!", show_alert=True)

    elif data == 'search':
        await callback_query.message.edit_text("📂 Janrni tanlang:", reply_markup=genre_menu)

    elif data.startswith('genre_'):
        genre = data.split('_', 1)[1]
        search_mode_users.add(user_id)
        genre_search_mode[user_id] = genre
        audio_search_mode_users.discard(user_id)
        await callback_query.message.edit_text(f"🔍 {genre.title()} kitoblar bo‘yicha qidiruv: nomini yozing", reply_markup=back_menu)

    elif data == 'search_audio':
        audio_search_mode_users.add(user_id)
        search_mode_users.discard(user_id)
        genre_search_mode.pop(user_id, None)
        await callback_query.message.edit_text("🎧 Audio kitob nomini yozing:", reply_markup=back_menu)

    elif data == 'clear_chat':
        await callback_query.message.edit_text("❓ Siz chatdagi barcha xabarlarni o‘chirmoqchimisiz?", reply_markup=confirm_menu)

    elif data == 'confirm_clear':
        for msg_id in user_messages[user_id]:
            try:
                await bot.delete_message(callback_query.message.chat.id, msg_id)
            except:
                continue
        user_messages[user_id].clear()
        await callback_query.message.answer("✅ Chat tozalandi.", reply_markup=main_menu)

    elif data == 'contact':
        await callback_query.message.edit_text("Murojaat uchun: https://t.me/AllBooksHub_uz", reply_markup=back_menu)

    elif data == 'admin_panel':
        phone = user_phone_map.get(user_id)
        if phone == ADMIN_PHONE:
            menu = InlineKeyboardMarkup(row_width=1)
            menu.add(
                InlineKeyboardButton("📢 Reklama yuborish", callback_data="send_broadcast"),
                InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="show_users"),
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back")
            )
            await callback_query.message.edit_text("Admin paneliga xush kelibsiz:", reply_markup=menu)
        else:
            await callback_query.answer("Siz admin emassiz!", show_alert=True)

    elif data == 'send_broadcast':
        await callback_query.message.edit_text("📨 Reklama matnini yuboring yoki media ilova qiling.")

    elif data == 'show_users':
        now = time.time()
        online = sum(1 for t in last_active.values() if now - t < 300)
        total = len(all_users)
        await callback_query.message.edit_text(f"🟢 Aktiv foydalanuvchilar: {online} ta\n📊 Umumiy foydalanuvchilar: {total} ta", reply_markup=back_menu)

    elif data == 'back':
        search_mode_users.discard(user_id)
        audio_search_mode_users.discard(user_id)
        genre_search_mode.pop(user_id, None)
        await callback_query.message.edit_text("Asosiy menyu:", reply_markup=main_menu)

@dp.message_handler(content_types=types.ContentType.ANY)
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    last_active[user_id] = time.time()
    all_users.add(user_id)
    user_messages[user_id].append(message.message_id)

    if not await check_user_in_channel(user_id):
        await message.delete()
        return

    if user_phone_map.get(user_id) == ADMIN_PHONE:
        for uid in all_users:
            try:
                await bot.copy_message(uid, message.chat.id, message.message_id)
            except:
                pass
        try:
            await bot.copy_message(CHANNEL_CHAT_ID, message.chat.id, message.message_id)
        except:
            pass
        return

    if user_limits[user_id]['book'] > DAILY_LIMIT or user_limits[user_id]['audio'] > DAILY_LIMIT:
        await message.answer("⛔ Siz bugungi limitga yetdingiz!")
        return

    if user_id in search_mode_users:
        user_limits[user_id]['book'] += 1
        msg = await message.answer_animation("https://media.giphy.com/media/3o7qE1YN7aBOFPRw8E/giphy.gif", caption="⏳ Yuklanmoqda...")
        user_messages[user_id].append(msg.message_id)
        await handle_book_search(message, genre_search_mode.get(user_id))
        time.sleep(10)
        await bot.delete_message(message.chat.id, msg.message_id)

    elif user_id in audio_search_mode_users:
        user_limits[user_id]['audio'] += 1
        msg = await message.answer_animation("https://media.giphy.com/media/3o7qE1YN7aBOFPRw8E/giphy.gif", caption="⏳ Yuklanmoqda...")
        user_messages[user_id].append(msg.message_id)
        await handle_audio_search(message)
        time.sleep(3)
        await bot.delete_message(message.chat.id, msg.message_id)
    else:
        await message.delete()

async def handle_book_search(message: types.Message, genre=None):
    query = normalize(message.text)
    search_stats[query] += 1
    matched_files = []

    folder = os.path.join(KITOBLAR_PAPKA, genre) if genre else KITOBLAR_PAPKA

    if not os.path.exists(folder):
        await message.answer("❌ Tanlangan janr uchun papka topilmadi. Admin bilan bog‘laning.")
        return

    for filename in os.listdir(folder):
        if filename.lower().endswith(".pdf"):
            if query in normalize(filename):
                matched_files.append(filename)
        if len(matched_files) >= 10:
            break

    if matched_files:
        for file in matched_files:
            path = os.path.join(folder, file)
            with open(path, 'rb') as doc:
                sent = await message.answer_document(doc)
                user_messages[message.from_user.id].append(sent.message_id)
    else:
        await message.answer("❌ Uzr, bu nomdagi kitob topilmadi.")

async def handle_audio_search(message: types.Message):
    query = normalize(message.text)
    search_stats[query] += 1
    matched_files = []

    if not os.path.exists(AUDIO_PAPKA):
        await message.answer("❌ Audio kitoblar papkasi topilmadi. Admin bilan bog‘laning.")
        return

    for filename in os.listdir(AUDIO_PAPKA):
        if filename.lower().endswith(".mp3"):
            if query in normalize(filename):
                matched_files.append(filename)
        if len(matched_files) >= 10:
            break

    if matched_files:
        for file in matched_files:
            path = os.path.join(AUDIO_PAPKA, file)
            with open(path, 'rb') as audio:
                sent = await message.answer_audio(audio)
                user_messages[message.from_user.id].append(sent.message_id)
    else:
        await message.answer("❌ Uzr, bu nomdagi audio topilmadi.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
