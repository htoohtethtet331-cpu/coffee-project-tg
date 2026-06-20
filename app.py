import requests
import json
import os
import time
from flask import Flask, request, jsonify, send_from_directory, render_template

app = Flask(__name__)

# ==================== [ ⚠️ API KEYS CONFIGURATION ] ====================
TELEGRAM_BOT_TOKEN = "8947073943:AAEUOXzSnXpXWYg4p60ohdsmownW5dU0wsw"   
TELEGRAM_CHAT_ID = "1967155608"       
IMGBB_API_KEY = "371d33f4a13209017e739a26fdb50c89"             
# =====================================================================

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data", "products.json")
ORDERS_FILE = os.path.join(BASE_DIR, "data", "orders.json")

# ── Products DB ──
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump([], f)

# ── Orders DB ──
if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w") as f:
        json.dump([], f)

def load_products():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_products(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_orders():
    with open(ORDERS_FILE, "r") as f:
        return json.load(f)

def save_orders(data):
    with open(ORDERS_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
        
    # ── /start or /help ──
    if text in ["/start", "/help"]:
        help_text = (
            "🏪 *CAPA CAFE - Admin Control Bot*\n\n"
            "💡 *Menu Commands:*\n"
            "• `/list` - Menu ပစ္စည်းစာရင်း ကြည့်ရန်\n"
            "• `/add နာမည်,ဈေးနှုန်း` - Menu ပစ္စည်းအသစ် တင်ရန်\n"
            "• `/delete နံပါတ်` - Menu ပစ္စည်း ဖျက်ရန်\n\n"
            "📦 *Order Commands:*\n"
            "• `/orders` - အော်ဒါအားလုံး ကြည့်ရန်\n"
            "• `/pending` - စောင့်ဆိုင်းဆဲ အော်ဒါများ ကြည့်ရန်\n"
            "• `/done နံပါတ်` - အော်ဒါ ပြီးဆုံးကြောင်း မှတ်ရန်\n"
            "• `/cancel နံပါတ်` - အော်ဒါ ပယ်ဖျက်ရန်\n\n"
            "ℹ️ _ဥပမာ- ပုံတစ်ပုံကို ရွေးပြီး Caption တွင် `/add Latte,3500` ဟု ရေး၍ ပို့ပေးပါ။_"
        )
        send_message(chat_id, help_text)
    
    # ── /list (products) ──
    elif text == "/list":
        products = load_products()
        if not products:
            send_message(chat_id, "❌ ဆိုင်မှာ Menu ပစ္စည်းစာရင်း မရှိသေးပါဗျာ။")
        else:
            msg = "📋 *လက်ရှိ Menu စာရင်းများ:*\n━━━━━━━━━━━━━━━\n"
            for idx, p in enumerate(products):
                msg += f"{idx + 1}. *{p['name']}* - {p['price']:,} MMK\n"
            send_message(chat_id, msg)
    
    # ── /orders (all orders) ──
    elif text == "/orders":
        orders = load_orders()
        if not orders:
            send_message(chat_id, "📭 အော်ဒါ မရှိသေးပါ။")
        else:
            msg = f"📦 *အော်ဒါစာရင်း (စုစုပေါင်း {len(orders)} ခု):*\n━━━━━━━━━━━━━━━\n"
            for idx, o in enumerate(orders[-10:]):  # နောက်ဆုံး ၁၀ ခုပဲ ပြ
                status_icon = "✅" if o['status'] == 'done' else ("❌" if o['status'] == 'cancelled' else "⏳")
                msg += (
                    f"{idx+1}. {status_icon} *{o['name']}*\n"
                    f"   📞 {o['phone']} | 💰 {o['total']:,} MMK\n"
                    f"   🕐 {o['time']}\n\n"
                )
            send_message(chat_id, msg)
    
    # ── /pending (pending orders only) ──
    elif text == "/pending":
        orders = load_orders()
        pending = [o for o in orders if o['status'] == 'pending']
        if not pending:
            send_message(chat_id, "✅ စောင့်ဆိုင်းဆဲ အော်ဒါ မရှိတော့ပါ!")
        else:
            msg = f"⏳ *စောင့်ဆိုင်းဆဲ အော်ဒါများ ({len(pending)} ခု):*\n━━━━━━━━━━━━━━━\n"
            for idx, o in enumerate(pending):
                msg += (
                    f"{idx+1}. *{o['name']}* (ID: `{o['id']}`)\n"
                    f"   📞 {o['phone']}\n"
                    f"   📍 {o['address']}\n"
                    f"   💰 {o['total']:,} MMK\n\n"
                )
            msg += "_/done နံပါတ် သို့မဟုတ် /cancel နံပါတ် ဖြင့် စီမံပါ_"
            send_message(chat_id, msg)
    
    # ── /done <number> ──
    elif text.startswith("/done"):
        try:
            idx = int(text.split(" ")[1]) - 1
            orders = load_orders()
            pending = [o for o in orders if o['status'] == 'pending']
            if 0 <= idx < len(pending):
                order_id = pending[idx]['id']
                for o in orders:
                    if o['id'] == order_id:
                        o['status'] = 'done'
                        save_orders(orders)
                        send_message(chat_id, f"✅ *{o['name']}* ရဲ့ အော်ဒါကို ပြီးဆုံးကြောင်း မှတ်လိုက်ပါပြီ!")
                        break
            else:
                send_message(chat_id, "❌ နံပါတ် မှားနေပါသည်။ `/pending` တွင် ပြန်စစ်ပါ။")
        except:
            send_message(chat_id, "❌ ဥပမာ - `/done 1` ဟု သုံးပါ။")

    # ── /cancel <number> ──
    elif text.startswith("/cancel"):
        try:
            idx = int(text.split(" ")[1]) - 1
            orders = load_orders()
            pending = [o for o in orders if o['status'] == 'pending']
            if 0 <= idx < len(pending):
                order_id = pending[idx]['id']
                for o in orders:
                    if o['id'] == order_id:
                        o['status'] = 'cancelled'
                        save_orders(orders)
                        send_message(chat_id, f"❌ *{o['name']}* ရဲ့ အော်ဒါကို ပယ်ဖျက်လိုက်ပါပြီ!")
                        break
            else:
                send_message(chat_id, "❌ နံပါတ် မှားနေပါသည်။ `/pending` တွင် ပြန်စစ်ပါ။")
        except:
            send_message(chat_id, "❌ ဥပမာ - `/cancel 1` ဟု သုံးပါ။")

    # ── /delete <number> (product) ──
    elif text.startswith("/delete"):
        try:
            idx_to_del = int(text.split(" ")[1]) - 1
            products = load_products()
            if 0 <= idx_to_del < len(products):
                removed = products.pop(idx_to_del)
                save_products(products)
                send_message(chat_id, f"✅ *{removed['name']}* ကို Menu ထဲမှ ဖျက်လိုက်ပါပြီ။")
            else:
                send_message(chat_id, "❌ ပစ္စည်းနံပါတ် မှားယွင်းနေပါသည်။ `/list` တွင် ပြန်စစ်ပါ။")
        except Exception:
            send_message(chat_id, "❌ ပုံစံမမှန်ပါ။ ဥပမာ- `/delete 1` ဟု သုံးပါ။")
            
    # ── /add (with photo) ──
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
                send_message(chat_id, f"✅ *{p_name}* ({p_price:,} MMK) ကို Menu တွင် ထည့်သွင်းပြီးပါပြီ!")
            else:
                send_message(chat_id, "❌ ပုံကို Server ပေါ်တင်ရတာ မအောင်မြင်ပါ။")
        except Exception as e:
            send_message(chat_id, f"❌ ပုံစံမမှန်ပါ။ ဥပမာ- `/add Coffee Name,3000` ဟု ရေးပါ။ ({e})")

    return "OK", 200

# ==================== [ 🌐 USER WEB API LOGIC ] ====================

@app.route('/')
def serve_frontend():
    return render_template('index.html')

@app.route('/First.html')
def serve_first():
    return render_template('First.html')

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

    # ── Save Order to orders.json ──
    orders = load_orders()
    new_order = {
        "id": str(int(time.time())),
        "name": name,
        "phone": phone,
        "address": address,
        "items": items,
        "total": grand_total,
        "screenshot": uploaded_img_url,
        "status": "pending",
        "time": time.strftime("%Y-%m-%d %H:%M", time.localtime())
    }
    orders.append(new_order)
    save_orders(orders)

    # ── Send to Telegram ──
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
        f"🆔 Order ID: <code>{new_order['id']}</code>\n"
        "👉 <i>ငွေလွှဲပြေစာအား စစ်ဆေးပြီး အော်ဒါအား အတည်ပြုပေးပါ။</i>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    res = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "photo": uploaded_img_url, "caption": telegram_message, "parse_mode": "HTML"})

    if res.json().get("ok"):
        return jsonify({"success": True}), 200
    return jsonify({"success": False}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
