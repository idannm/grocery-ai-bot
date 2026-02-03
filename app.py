import streamlit as st
from groq import Groq
import psycopg2
import requests

# הגדרות מפתחות מהכספת (Secrets)
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
DB_URL = st.secrets["DB_URL"]
MAKE_WEBHOOK_URL = st.secrets.get("MAKE_WEBHOOK_URL", "") # נוסיף את זה בהמשך ל-Secrets

client = Groq(api_key=GROQ_API_KEY)

# פונקציה לשמירת הזמנה ב-Neon
def save_order_to_db(customer_name, order_text):
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO orders (customer_name, order_content) VALUES (%s, %s)", (customer_name, order_text))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Error saving to DB: {e}")

# פונקציה ששולחת את התשובה חזרה לוואטסאפ דרך Make
def send_to_whatsapp(message, customer_number):
    if MAKE_WEBHOOK_URL:
        data = {"message": message, "number": customer_number}
        requests.post(MAKE_WEBHOOK_URL, json=data)

st.title("🛒 בוט ההזמנות שלי - ניהול וואטסאפ")

# ממשק בדיקה באתר (כדי שתוכל להראות ללקוחות גם פה)
user_input = st.text_input("נסה את הבוט (כמו לקוח בוואטסאפ):")

if user_input:
    # שליחת השאלה ל-AI
    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "system", "content": "אתה עוזר חכם לחנות מכולת. תענה קצר ולעניין. אם הלקוח סיים להזמין, תגיד 'ההזמנה נשמרה'."},
                  {"role": "user", "content": user_input}]
    )
    
    response = completion.choices[0].message.content
    st.write(f"**הבוט עונה:** {response}")
    
    # אם הבוט זיהה סיום הזמנה - שומרים ל-DB
    if "נשמרה" in response:
        save_order_to_db("לקוח וואטסאפ", user_input)
        st.success("ההזמנה נרשמה במערכת!")

# --- לוגיקה לקבלת הודעות מוואטסאפ (דרך URL) ---
# הערה: כשנחבר את Make, הם ישלחו לכאן בקשות HTTP
query_params = st.query_params
if "whatsapp_msg" in query_params:
    msg = query_params["whatsapp_msg"]
    sender = query_params.get("sender", "unknown")
    # כאן אפשר להוסיף לוגיקה שתעבד אוטומטית הודעות נכנסות
