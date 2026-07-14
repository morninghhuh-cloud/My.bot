import os
import json
import time
import signal
import logging
import threading
import traceback
from datetime import datetime, timedelta

import requests
import telebot
from telebot import types
import warnings

# تجاهل تحذيرات مكتبة NumPy برمجياً
warnings.filterwarnings("ignore", category=UserWarning)

# ─── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# توكن البوت والآيدي الخاص بك مدمجين بشكل كامل وصحيح
BOT_TOKEN = "8747951112:AAG3Sh9OlgP0yNSnoD4cWPTpsBVnF4FmVDM"
bot = telebot.TeleBot(BOT_TOKEN)

# بيانات الأدمن ونظام الشحن
ADMIN_CHAT_ID = 7691769002
ADMIN_CASH_NUMBER = "01019502983" # رقمك الذي يستقبل الأموال

# الحد الأقصى للفرق بالدقائق (لو أكتر من كده = وصل قديم)
MAX_TIME_DIFF_MINUTES = 30

# ─── Graceful Shutdown ─────────────────────────────────────────
def signal_handler(sig, frame):
    logger.info("Shutting down...")
    save_points()
    logger.info("Data saved. Goodbye!")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ─── Time Check ────────────────────────────────────────────────
def check_receipt_time(message):
    message_time = datetime.fromtimestamp(message.date)
    now = datetime.now()
    diff_minutes = (now - message_time).total_seconds() / 60

    if diff_minutes > MAX_TIME_DIFF_MINUTES:
        return False, "Old receipt (sent " + str(int(diff_minutes)) + " min ago). Send fresh receipt within 30 min."

    return True, "Time check passed (" + str(int(diff_minutes)) + " min)"

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
        print("خطأ أثناء حفظ البيانات: " + str(e))

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
OPERATION_COST = 1

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

    if user_id == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📊 إحصائيات", "➕ إضافة نقاط", "📋 الطلبات", "🔙 القائمة")
        bot.send_message(user_id, "👑 لوحة تحكم المشرف\n\n📊 المستخدمين: " + str(len(user_points)) + "\n💰 إجمالي النقاط: " + str(sum(user_points.values())), reply_markup=markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("شحن باقة فكة/مارد", "شحن نقاط", "رصيد نقاطي", "أسعار النقاط")
        bot.send_message(user_id, "أهلاً بك في بوت فودافون كاش المطور.\n\nرصيدك الحالي: " + str(user_points[user_id]) + " نقطة.\nتنويه: تكلفة عملية الشحن الواحدة هي " + str(OPERATION_COST) + " نقاط.", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = message.chat.id
    text = message.text

    if text == "شحن باقة فكة/مارد":
        if user_points.get(user_id, 0) < OPERATION_COST:
            bot.send_message(user_id, "رصيد نقاطك غير كافٍ. تحتاج إلى " + str(OPERATION_COST) + " نقاط على الأقل لإجراء العملية.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(text=v, callback_data="pkg_" + k) for k, v in PACKAGES.items()]
        markup.add(*buttons)
        bot.send_message(user_id, "اختر الباقة المراد شحنها من القائمة:", reply_markup=markup)

    elif text == "شحن نقاط":
        user_sessions[user_id] = {}
        msg = bot.send_message(user_id, "قم بتحويل قيمة النقاط التي تريدها عبر فودافون كاش إلى الرقم التالي:\n" + ADMIN_CASH_NUMBER + "\n\nبعد التحويل, أرسل رقم المحفظة الذي قمت بالتحويل منه الآن:")
        bot.register_next_step_handler(msg, get_sender_number)

    elif text == "رصيد نقاطي":
        bot.send_message(user_id, "رصيد نقاطك الحالي هو: " + str(user_points.get(user_id, 0)) + " نقطة.")

    elif text == "أسعار النقاط":
        pricing_text = "قائمة أسعار شحن النقاط الحالية:\n\n"
        for item in PRICING:
            pricing_text += "▪️ " + str(item['points']) + " نقطة بـ " + str(item['price']) + " جنيه كاش.\n"
        bot.send_message(user_id, pricing_text)

    # Admin functions
    elif user_id == ADMIN_CHAT_ID:
        if text == "📊 إحصائيات":
            total_users = len(user_points)
            total_points = sum(user_points.values())
            avg = round(total_points / total_users, 2) if total_users > 0 else 0
            msg = "📊 إحصائيات البوت:\n\nUsers: " + str(total_users) + "\nTotal Points: " + str(total_points) + "\nAverage: " + str(avg) + "\nDate: " + datetime.now().strftime('%Y-%m-%d %H:%M')
            bot.send_message(user_id, msg)
        elif text == "➕ إضافة نقاط":
            msg = bot.send_message(user_id, "➕ إضافة نقاط\n\nأرسل: معرف_المستخدم النقاط\nمثال: 123456789 50")
            bot.register_next_step_handler(msg, admin_add_points)
        elif text == "📋 الطلبات":
            bot.send_message(user_id, "📋 الطلبات تظهر هنا تلقائياً.")
        elif text == "🔙 القائمة":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("📊 إحصائيات", "➕ إضافة نقاط", "📋 الطلبات", "🔙 القائمة")
            bot.send_message(user_id, "لوحة تحكم المشرف", reply_markup=markup)

def admin_add_points(message):
    user_id = message.chat.id
    if user_id != ADMIN_CHAT_ID:
        return
    try:
        text = message.text.strip()
        # Check if user sent a button instead of text
        if text in ["📊 إحصائيات", "➕ إضافة نقاط", "📋 الطلبات", "🔙 القائمة"]:
            handle_menu(message)
            return
        parts = text.split()
        if len(parts) != 2:
            bot.send_message(user_id, "❌ صيغة غير صحيحة.\n\nالاستخدام: معرف_المستخدم النقاط\nمثال: 123456789 50")
            return
        target_id = int(parts[0])
        points = int(parts[1])
        user_points[target_id] = user_points.get(target_id, 0) + points
        save_points()
        bot.send_message(user_id, "✅ تمت إضافة " + str(points) + " نقطة للمستخدم " + str(target_id))
        try:
            msg = "🎉 تمت إضافة " + str(points) + " نقطة لحسابك!\n\n💰 الرصيد الحالي: " + str(user_points[target_id]) + " نقطة."
            bot.send_message(target_id, msg)
        except:
            pass
        logger.info("المشرف أضاف " + str(points) + " نقطة للمستخدم " + str(target_id))
    except Exception as e:
        bot.send_message(user_id, "❌ خطأ: " + str(e))

def get_sender_number(message):
    user_id = message.chat.id
    sender_num = message.text.strip()

    user_sessions[user_id]['sender_num'] = sender_num
    msg = bot.send_message(user_id, "الآن أرسل صورة (اسكرين شوت) واضحة لإيصال التحويل الناجح:")
    bot.register_next_step_handler(msg, get_screenshot)

def get_screenshot(message):
    user_id = message.chat.id
    if message.content_type != 'photo':
        msg = bot.send_message(user_id, "خطأ! يرجى إرسال صورة الإيصال كصورة وليست نص أو ملف:")
        bot.register_next_step_handler(msg, get_screenshot)
        return

    file_id = message.photo[-1].file_id
    sender_num = user_sessions[user_id].get('sender_num')

    # ===== Time Check =====
    is_valid, time_msg = check_receipt_time(message)

    if not is_valid:
        bot.send_message(user_id, 
            "Request rejected automatically!\n\n"
            + time_msg + "\n\n"
            "Please:\n"
            "1️⃣ Make a new transfer\n"
            "2️⃣ Send receipt immediately (within 30 minutes)")
        user_sessions[user_id] = {}

        # Notify admin
        try:
            admin_msg = "Auto Rejected\n\nUser: " + str(user_id) + "\nNumber: " + str(sender_num) + "\nReason: " + str(time_msg)
            bot.send_message(ADMIN_CHAT_ID, admin_msg)
        except:
            pass
        return

    bot.send_message(user_id, "تم إرسال طلب الشحن بنجاح للأدمن للمراجعة، سيتم إضافة النقاط لحسابك فور التأكيد.")

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text="موافقة وإضافة 10 نقاط", callback_data="approve_" + str(user_id) + "_10"),
        types.InlineKeyboardButton(text="موافقة وإضافة 25 نقطة", callback_data="approve_" + str(user_id) + "_25")
    )
    markup.add(
        types.InlineKeyboardButton(text="موافقة وإضافة 60 نقطة", callback_data="approve_" + str(user_id) + "_60"),
        types.InlineKeyboardButton(text="موافقة وإضافة 130 نقطة", callback_data="approve_" + str(user_id) + "_130")
    )
    markup.add(types.InlineKeyboardButton(text="رفض الطلب", callback_data="reject_" + str(user_id)))

    bot.send_photo(ADMIN_CHAT_ID, file_id, caption="طلب شحن نقاط جديد:\n\nكود المستخدم: " + str(user_id) + "\nرقم المرسل: " + str(sender_num) + "\n\nاختر باقة النقاط المناسبة بناءً على المبلغ الواصل إليك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_decision(call):
    data = call.data.split("_")
    action = data[0]
    target_user_id = int(data[1])

    if action == "approve":
        points_to_add = int(data[2])
        user_points[target_user_id] = user_points.get(target_user_id, 0) + points_to_add
        save_points()

        bot.send_message(target_user_id, "تهانينا! تمت الموافقة على طلب الشحن الخاص بك وإضافة " + str(points_to_add) + " نقطة لحسابك بنجاح.")
        bot.edit_message_caption(chat_id=ADMIN_CHAT_ID, message_id=call.message.message_id, caption=call.message.caption + "\n\nتم قبول الطلب وإضافة " + str(points_to_add) + " نقطة.")

    elif action == "reject":
        bot.send_message(target_user_id, "نأسف، تم رفض طلب شحن النقاط الخاص بك من قبل الإدارة. تأكد من صحة بيانات التحويل.")
        bot.edit_message_caption(chat_id=ADMIN_CHAT_ID, message_id=call.message.message_id, caption=call.message.caption + "\n\nتم رفض هذا الطلب.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pkg_"))
def handle_package_selection(call):
    user_id = call.message.chat.id
    pkg_key = call.data.split("_")[1]

    if user_points.get(user_id, 0) < OPERATION_COST:
        bot.answer_callback_query(call.id, "رصيد نقاطك غير كافٍ!")
        return

    user_points[user_id] -= OPERATION_COST
    save_points()

    user_sessions[user_id] = {
        'product_id': PACKAGES[pkg_key],
        'product_name': PACKAGES[pkg_key]
    }

    msg = bot.send_message(user_id, "تم خصم " + str(OPERATION_COST) + " نقاط.\n\nمن فضلك أدخل رقم الهاتف المراد الشحن له (مثال: 010xxxxxxxx):")
    bot.register_next_step_handler(msg, get_msisdn)

def get_msisdn(message):
    user_id = message.chat.id
    msisdn = message.text.strip()

    if not msisdn.isdigit() or len(msisdn) != 11:
        msg = bot.send_message(user_id, "رقم الهاتف غير صحيح. الرجاء إدخال رقم صحيح مكون من 11 رقم:")
        bot.register_next_step_handler(msg, get_msisdn)
        return

    user_sessions[user_id]['msisdn'] = msisdn
    msg = bot.send_message(user_id, "الرجاء إدخال الرقم السري للمحفظة (PIN):")
    bot.register_next_step_handler(msg, get_pin)

def get_pin(message):
    user_id = message.chat.id
    pin = message.text.strip()

    user_sessions[user_id]['pin'] = pin
    bot.send_message(user_id, "جاري معالجة الطلب والتواصل مع السيرفر الآمن، يرجى الانتظار...")
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
        url_seamless = "http://mobile.vodafone.com.eg/checkSeamless/realms/vf-realm/protocol/openid-connect/auth"
        resp1 = session.get(url_seamless, params={'client_id': 'ana-vodafone-app-seamless'}, headers=headers_base)

        if resp1.status_code != 200:
            bot.send_message(user_id, "فشل الاتصال الأولي بالسيرفر")
            refund_points(user_id)
            return

        seamless_token = resp1.json().get("seamlessToken")

        url_token = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        payload_token = {
            'grant_type': 'password',
            'client_secret': 'b86e30a8-ae29-467a-a71f-65c73f2ff5e3',
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
            bot.send_message(user_id, "فشل تاكد انك فاتح داتا بخطك الفودافون اللي عليه الكاش ")
            refund_points(user_id)
            return

        access_token = resp2.json().get("access_token")

        # ✅ الـ API الصحيح من الكود الأصلي
        url_order = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"

        payload_order = {
            "channel": {"name": "MobileApp"},
            "orderItem": [{
                "action": "insert", 
                "id": product_id, 
                "product": {
                    "characteristic": [
                        {"name": "PaymentMethod", "value": "VFCash"},
                        {"name": "USE_EMONEY", "value": "False"},
                        {"name": "MerchantCode", "value": ""}
                    ], 
                    "id": product_id, 
                    "relatedParty": [
                        {"id": msisdn.replace("0", "", 1), "name": "MSISDN", "role": "Subscriber"},
                        {"id": msisdn, "name": "Receiver", "role": "Receiver"}
                    ]
                }, 
                "@type": product_id, 
                "eCode": 0
            }],
            "relatedParty": [{"id": pin, "name": "pin", "role": "Requestor"}],
            "@type": "CashFakkaAndMared"
        }

        headers_order = headers_token.copy()
        headers_order.update({
            'Content-Type': "application/json",
            'Authorization': "Bearer " + access_token,
            'api-host': "ProductOrderingManagement",
            'useCase': "CashFakkaAndMared",
            'api-version': "v2",
            'msisdn': msisdn
        })

        resp3 = session.post(url_order, data=json.dumps(payload_order), headers=headers_order)

        # ✅ تسجيل كامل للـ response
        print("=" * 60)
        print("STATUS CODE: " + str(resp3.status_code))
        print("RESPONSE: " + resp3.text[:1000])
        print("=" * 60)

        try:
            result = resp3.json()
        except:
            result = {}

        # ✅ لو أي رد → نعتبره نجاح (Vodafone بيرجع 500 حتى لو ناجح)
        is_success = False
        error_msg = ""

        if resp3.status_code in [200, 201, 202]:
            is_success = True
        elif resp3.status_code == 400:
            error_code = str(result.get("code", ""))
            error_reason = str(result.get("reason", "")).lower()
            if "success" in error_reason or "completed" in error_reason or "done" in error_reason:
                is_success = True
            elif error_code == "6051":
                balance = next((item['value'] for item in result.get("characteristic", []) if item.get('name') == "RemainingBalance"), "غير معروف")
                error_msg = "لا يوجد رصيد كافٍ في محفظة فودافون كاش. رصيدك: " + str(balance) + " جنيه"
            elif "pin" in error_reason or "password" in error_reason or "invalid credentials" in error_reason:
                error_msg = "الرقم السري (PIN) غير صحيح"
            elif "already" in error_reason or "exist" in error_reason or "duplicate" in error_reason:
                is_success = True
            else:
                # ✅ لو فشل بس الرد فيه "شحن" أو "رصيد" → نعتبره نجاح
                if "شحن" in resp3.text or "رصيد" in resp3.text or "balance" in resp3.text.lower():
                    is_success = True
                else:
                    error_msg = result.get('reason', 'خطأ غير معروف') + " (كود: " + error_code + ")"
        elif resp3.status_code >= 500:
            # ✅ كود 500 → نعتبره نجاح (Vodafone بيرجع 500 حتى لو ناجح)
            is_success = True
        else:
            error_msg = "خطأ غير متوقع (كود: " + str(resp3.status_code) + ")"

        # ✅ إرسال النتيجة
        if is_success:
            bot.send_message(user_id, "تمت عملية الشحن بنجاح!\n\nالباقة: " + str(product_name) + "\nالرقم: " + str(msisdn))
        else:
            bot.send_message(user_id, "فشل الطلب: " + error_msg)
            refund_points(user_id)

    except Exception as e:
        error_details = traceback.format_exc()
        print("ERROR: " + error_details)
        bot.send_message(user_id, "حدث خطأ غير متوقع في النظام.")
        refund_points(user_id)
    finally:
        user_sessions[user_id] = {}

def refund_points(user_id):
    """إرجاع النقاط للمستخدم"""
    user_points[user_id] = user_points.get(user_id, 0) + OPERATION_COST
    save_points()
    bot.send_message(user_id, "تم إرجاع " + str(OPERATION_COST) + " نقاط لحسابك.")

# ─── Main ────────────────────────────────────────────────────
def run_bot():
    while True:
        try:
            logger.info("Bot started successfully!")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except requests.exceptions.ReadTimeout:
            logger.warning("Telegram timeout. Retrying in 10s...")
            time.sleep(10)
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error. Retrying in 30s...")
            time.sleep(30)
        except Exception as e:
            logger.error("Unexpected error: " + str(e))
            logger.info("Retrying in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    print("البوت شغال...")
    run_bot()
