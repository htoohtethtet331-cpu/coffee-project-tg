import requests
import json
import os
import time
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# ==================== [ ⚠️ API KEYS CONFIGURATION ] ====================
TELEGRAM_BOT_TOKEN = "8142082008:AAFdWGm7K4Ql7l-ytZON6-FjMtoLAGQlgT4"   
TELEGRAM_CHAT_ID = "7345558963"       
IMGBB_API_KEY = "371d33f4a13209017e739a26fdb50c89"             
# =====================================================================

DB_FILE = "products.json"

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump([], f)

def load_products():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_products(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def upload_to_imgbb(file_bytes, filename):
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY}
        files = {"image": (filename, file_bytes)}
        response = requests.post(url, data=payload, files=files, timeout=20)
        res_data = response.json()
        if res_data.get("success"):
            return res_data["data"]["url"]
        return None
    except Exception as e:
        print(f"Imgbb Error: {e}")
        return None

def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    )

# ==================== [ 🤖 TELEGRAM BOT WEBHOOK ] ====================

@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    # URL ကို အလိုအလျောက် Webhook အဖြစ် သတ်မှတ်ပေးမည့် Route
    host_url = request.host_url.rstrip('/')
    webhook_url = f"{host_url}/webhook"
    res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}")
    return jsonify({"message": "Webhook setup completed", "response": res.json()})

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return "OK", 200
        
    message = update["message"]
    chat_id = str(message.get("chat", {}).get("id"))
    text = message.get("text", "")
    
    if chat_id != TELEGRAM_CHAT_ID:
        return "OK", 200
        
    if text in ["/start", "/help"]:
        help_text = (
            "🏪 *CAPA CAFE - Admin Control Bot*\n\n"
            "💡 *အသုံးပြုနိုင်သော Commands များ:*\n"
            "• `/list` - ပစ္စည်းစာရင်းအားလုံး ကြည့်ရန်\n"
            "• `/add နာမည်,ဈေးနှုန်း` - ပစ္စည်းအသစ်တင်ရန် (ဓာတ်ပုံကို Caption တွင် ဤစာသားထည့်၍ ပို့ပါ)\n"
            "• `/delete ပစ္စည်းနံပါတ်` - ပစ္စည်းကို ဖျက်ရန်\n\n"
            "ℹ️ _ဥပမာ- ပုံတစ်ပုံကို ရွေးပြီး Caption တွင် `/add Latte,3500` ဟု ရေး၍ ပို့ပေးပါ။_"
        )
        send_message(chat_id, help_text)
        
    elif text == "/list":
        products = load_products()
        if not products:
            send_message(chat_id, "❌ ဆိုင်မှာ ပစ္စည်းစာရင်း မရှိသေးပါဗျာ။")
        else:
            msg = "📋 *လက်ရှိ ပစ္စည်းစာရင်းများ:*\n━━━━━━━━━━━━━━━\n"
            for idx, p in enumerate(products):
                msg += f"{idx + 1}. *{p['name']}* - {p['price']:,} MMK\nID: `{p['id']}`\n\n"
            send_message(chat_id, msg)
            
    elif text.startswith("/delete"):
        try:
            idx_to_del = int(text.split(" ")[1]) - 1
            products = load_products()
            if 0 <= idx_to_del < len(products):
                removed = products.pop(idx_to_del)
                save_products(products)
                send_message(chat_id, f"✅ *{removed['name']}* ကို စနစ်ထဲမှ ဖျက်လိုက်ပါပြီ။")
            else:
                send_message(chat_id, "❌ ပစ္စည်းနံပါတ် မှားယွင်းနေပါသည်။ `/list` တွင် ပြန်စစ်ပါ။")
        except Exception:
            send_message(chat_id, "❌ ပုံစံမမှန်ပါ။ ဥပမာ- `/delete 1` ဟု သုံးပါ။")
            
    elif "photo" in message and message.get("caption", "").startswith("/add"):
        caption = message.get("caption", "")
        try:
            data_part = caption.replace("/add ", "").split(",")
            p_name = data_part[0].strip()
            p_price = int(data_part[1].strip())
            
            photo_file_id = message["photo"][-1]["file_id"]
            file_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile", params={"file_id": photo_file_id}).json()
            file_path = file_info["result"]["file_path"]
            file_bytes = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}").content
            
            img_url = upload_to_imgbb(file_bytes, f"{p_name}.jpg")
            
            if img_url:
                products = load_products()
                new_product = {
                    "id": str(int(time.time())),
                    "name": p_name,
                    "price": p_price,
                    "image": img_url
                }
                products.append(new_product)
                save_products(products)
                send_message(chat_id, f"📊 *သိမ်းဆည်းမှု အောင်မြင်ပါသည်!*\n• ပစ္စည်း: {p_name}\n• ဈေးနှုန်း: {p_price:,} MMK")
            else:
                send_message(chat_id, "❌ ပုံကို Server ပေါ်တင်ရတာ မအောင်မြင်ပါ။")
        except Exception as e:
            send_message(chat_id, f"❌ ပုံစံမမှန်ပါ။ ဥပမာ- `/add Coffee Name,3000` ဟု ရေးပါ။ ({e})")

    return "OK", 200

# ==================== [ 🌐 USER WEB API LOGIC ] ====================

@app.route('/')
def serve_frontend():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(load_products()), 200

@app.route('/api/order', methods=['POST'])
def handle_order():
    name = request.form.get('customer_name')
    phone = request.form.get('customer_phone')
    address = request.form.get('customer_address')
    items = json.loads(request.form.get('items', '[]'))
    screenshot_file = request.files.get('screenshot')

    if not name or not phone or not address or not screenshot_file:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    uploaded_img_url = upload_to_imgbb(screenshot_file.stream.read(), screenshot_file.filename)
    if not uploaded_img_url:
        return jsonify({"success": False, "message": "Image upload failed"}), 500

    items_text = ""
    grand_total = 0
    for item in items:
        item_total = int(item['price']) * int(item['qty'])
        grand_total += item_total
        items_text += f"• <b>{item['name']}</b> ({int(item['price']):,} x {item['qty']}) = {item_total:,} MMK\n"

    telegram_message = (
        "☕️ <b>CAPA CAFE - အော်ဒါအသစ် ရောက်ရှိပါပြီ။</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>ဝယ်ယူသူအမည်:</b> {name}\n"
        f"📞 <b>ဖုန်းနံပါတ်:</b> {phone}\n"
        f"📍 <b>ပို့ဆောင်ရမည့်လိပ်စာ:</b> {address}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🛍️ <b>မှာယူသည့်ပစ္စည်းများ-</b>\n"
        f"{items_text}"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>စုစုပေါင်း ကျသင့်ငွေ:</b> <code>{grand_total:,} MMK</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "👉 <i>ငွေလွှဲပြေစာအား စစ်ဆေးပြီး အော်ဒါအား အတည်ပြုပေးပါ။</i>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    res = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "photo": uploaded_img_url, "caption": telegram_message, "parse_mode": "HTML"})

    if res.json().get("ok"):
        return jsonify({"success": True}), 200
    return jsonify({"success": False}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
