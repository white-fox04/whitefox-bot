import os
import sqlite3
import time
import re
from datetime import datetime
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
COOLDOWN_MINUTES = int(os.getenv("COOLDOWN_MINUTES", "300"))
APP_LINK = os.getenv("APP_LINK", "https://t.me/files6865/293")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/WHITEFOX03")
NO_COOLDOWN_IDS = set(map(int, os.getenv("NO_COOLDOWN_IDS", "").split(','))) if os.getenv("NO_COOLDOWN_IDS") else set()
MRVN_USERNAME = os.getenv("MRVN_USERNAME")
MRVN_PASSWORD = os.getenv("MRVN_PASSWORD")

DB_FILE = "users.db"

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    last_request INTEGER DEFAULT 0,
    points INTEGER DEFAULT 1
)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    key_text TEXT,
    created_at INTEGER
)''')
conn.commit()

def generate_mrvn_key():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    login_url = "https://putraxit.cyou/public/login"
    gen_url = "https://putraxit.cyou/public/keys/generate"
    try:
        resp = session.get(login_url, timeout=15)
        csrf = re.search(r'<input type="hidden" name="csrf_test_name" value="([^"]+)"', resp.text)
        if not csrf: return None
        csrf_token = csrf.group(1)
        login_data = {
            'csrf_test_name': csrf_token,
            'username': MRVN_USERNAME,
            'password': MRVN_PASSWORD,
            'stay_log': 'yes'
        }
        login_resp = session.post(login_url, data=login_data, timeout=15)
        if "Invalid username or password" in login_resp.text: return None
        resp_gen = session.get(gen_url, timeout=15)
        csrf_gen = re.search(r'<input type="hidden" name="csrf_test_name" value="([^"]+)"', resp_gen.text)
        if not csrf_gen: return None
        csrf_token_gen = csrf_gen.group(1)
        gen_data = {
            'csrf_test_name': csrf_token_gen,
            'game': 'STRICKSBR',
            'key_type': 'regular',
            'max_devices': '1',
            'duration': '24',
            'key_mode': 'auto_userpass',
            'loopcount': '1'
        }
        result = session.post(gen_url, data=gen_data, timeout=15)
        key_match = re.search(r'<code[^>]*id="keyText"[^>]*>([^<]+)</code>', result.text)
        if key_match: return key_match.group(1).strip()
        key_match2 = re.search(r'([a-zA-Z0-9]+:[a-zA-Z0-9]+)', result.text)
        if key_match2: return key_match2.group(1)
        return None
    except Exception:
        return None

async def show_main_menu(update, text="✨ *القائمة الرئيسية* ✨"):
    keyboard = [
        [InlineKeyboardButton("🎁 احصل على مفتاح", callback_data="get_key")],
        [InlineKeyboardButton("📊 معلومات حسابي", callback_data="my_info")],
        [InlineKeyboardButton("📜 تاريخ مفاتيحي", callback_data="my_keys")],
        [InlineKeyboardButton("📱 التطبيق", url=APP_LINK)],
        [InlineKeyboardButton("📢 القناة الرسمية", url=CHANNEL_LINK)]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("INSERT OR IGNORE INTO users (user_id, last_request, points) VALUES (?, ?, ?)", (user_id, 0, 1))
    conn.commit()
    keyboard = [
        [InlineKeyboardButton("🎁 احصل على مفتاح", callback_data="get_key")],
        [InlineKeyboardButton("📊 معلومات حسابي", callback_data="my_info")],
        [InlineKeyboardButton("📜 تاريخ مفاتيحي", callback_data="my_keys")],
        [InlineKeyboardButton("📱 التطبيق", url=APP_LINK)],
        [InlineKeyboardButton("📢 القناة الرسمية", url=CHANNEL_LINK)]
    ]
    await update.message.reply_text(
        f"✨ مرحباً بك يا {update.effective_user.first_name}! ✨\n\n"
        "أنا بوت WHITE FOX، يمكنك الحصول على مفاتيح تفعيل مجانية.\n"
        "• كل مفتاح صالح لمدة 24 ساعة.\n"
        "• مفتاح واحد كل 5 ساعات (إلا إذا كنت مستثنى).\n"
        "• اضغط الزر أدناه.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data

    try:
        await query.message.delete()
    except:
        pass

    if data == "get_key":
        c.execute("SELECT last_request, points FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            c.execute("INSERT INTO users (user_id, last_request, points) VALUES (?, ?, ?)", (user_id, 0, 1))
            conn.commit()
            last_req = 0
        else:
            last_req, _ = row

        now = int(time.time())
        is_exempt = (user_id in NO_COOLDOWN_IDS)

        if not is_exempt and (now - last_req) < COOLDOWN_MINUTES * 60:
            remaining = COOLDOWN_MINUTES * 60 - (now - last_req)
            hours_left = remaining // 3600
            mins_left = (remaining % 3600) // 60
            msg = await query.message.reply_text(f"⏳ لا يمكنك الحصول على مفتاح الآن.\nيجب الانتظار {hours_left} ساعة و {mins_left} دقيقة.")
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except:
                pass
            await show_main_menu(update, "✨ *القائمة الرئيسية* ✨")
            return

        processing_msg = await query.message.reply_text("⏳")
        key = generate_mrvn_key()
        try:
            await processing_msg.delete()
        except:
            pass

        if key:
            if not is_exempt:
                c.execute("UPDATE users SET last_request = ? WHERE user_id = ?", (now, user_id))
                conn.commit()
            c.execute("INSERT INTO user_keys (user_id, key_text, created_at) VALUES (?, ?, ?)", (user_id, key, now))
            conn.commit()

            result_text = f"✅ مفتاحك:\n`{key}`\n\nصلاحية: 24 ساعة\nاستخدمه فوراً."
            keyboard = [
                [InlineKeyboardButton("🎁 مفتاح آخر", callback_data="get_key")],
                [InlineKeyboardButton("📊 معلوماتي", callback_data="my_info")],
                [InlineKeyboardButton("📜 تاريخ مفاتيحي", callback_data="my_keys")]
            ]
            await query.message.reply_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            error_text = "❌ فشل توليد المفتاح. حاول مجدداً بعد دقائق."
            await query.message.reply_text(error_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]))
        return

    elif data == "my_info":
        c.execute("SELECT last_request, points FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        is_exempt = (user_id in NO_COOLDOWN_IDS)
        if row:
            last_req, _ = row
            last_str = datetime.fromtimestamp(last_req).strftime("%Y-%m-%d %H:%M:%S") if last_req else "لم تطلب بعد"
            cooldown_status = "🚫 معفى من التبريد" if is_exempt else f"⏳ {COOLDOWN_MINUTES} دقيقة"
            msg = f"📊 معلوماتك:\n🆔 {user_id}\n📅 آخر طلب: {last_str}\n⏱️ حالة التبريد: {cooldown_status}"
        else:
            msg = "لا توجد بيانات."
        await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]))
        return

    elif data == "my_keys":
        c.execute("SELECT key_text, created_at FROM user_keys WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))
        rows = c.fetchall()
        if rows:
            text = "📜 *آخر مفاتيحك:*\n\n"
            for i, (key_text, ts) in enumerate(rows, 1):
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                text += f"{i}. `{key_text}`  \\- {date_str}\n"
            await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]))
        else:
            await query.message.reply_text("لم تقم بإنشاء أي مفتاح بعد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]))
        return

    elif data == "back":
        keyboard = [
            [InlineKeyboardButton("🎁 احصل على مفتاح", callback_data="get_key")],
            [InlineKeyboardButton("📊 معلومات حسابي", callback_data="my_info")],
            [InlineKeyboardButton("📜 تاريخ مفاتيحي", callback_data="my_keys")],
            [InlineKeyboardButton("📱 التطبيق", url=APP_LINK)],
            [InlineKeyboardButton("📢 القناة الرسمية", url=CHANNEL_LINK)]
        ]
        await query.message.reply_text("✨ *القائمة الرئيسية* ✨", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("استخدم الأزرار فقط. اكتب /start لإظهار القائمة.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND, start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))
    print("✅ البوت يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
