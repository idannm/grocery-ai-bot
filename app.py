import streamlit as st
from groq import Groq
import psycopg2
import pandas as pd
import requests

# --- הגדרות מהכספת ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
DB_URL = st.secrets["DB_URL"]

client = Groq(api_key=GROQ_API_KEY)

# --- פונקציות עזר ---
def get_db_connection():
    return psycopg2.connect(DB_URL)

def get_inventory():
    try:
        conn = get_db_connection()
        query = "SELECT DISTINCT ON (name) name, price, stock FROM products ORDER BY name, id DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_string(index=False)
    except Exception as e:
        return "המלאי לא זמין כרגע."

def save_order_to_db(customer_name, order_text):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO orders (customer_name, order_content) VALUES (%s, %s)", (customer_name, order_text))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Error saving to DB: {e}")

# --- לוגיקה עבור Make.com (חייב להופיע לפני ה-UI) ---
if "message" in st.query_params:
    user_msg = st.query_params["message"]
    inventory_data = get_inventory()
    
    system_msg = f"אתה עוזר במכולת שכונתית וחברית. המלאי שלך:\n{inventory_data}\n"
    system_msg += "הוראות: אל תהיה רשמי! השתמש בשמות חיבה כמו 'צדיק'. בסוף הזמנה בקש שם וכתובת."
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]
        )
        ai_reply = completion.choices[0].message.content
        
        # אם הבוט זיהה סיום הזמנה - שומרים ל-DB
        if "נשמרה" in ai_reply or "הזמנה בוצעה" in ai_reply:
             save_order_to_db("לקוח וואטסאפ", user_msg)

        # פלט נקי עבור Make
        st.write(ai_reply)
        st.stop() # חשוב! עוצר את הטעינה של שאר האתר
    except Exception as e:
        st.write(f"Error: {e}")
        st.stop()

# --- ממשק האתר (מה שרואים בדפדפן) ---
st.title("🛒 המכולת החכמה - ניהול ובדיקה")
user_input = st.text_input("בדיקת צ'אט (כמו לקוח):")

if user_input:
    inventory_data = get_inventory()
    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "system", "content": f"עוזר במכולת. מלאי:\n{inventory_data}"},
                  {"role": "user", "content": user_input}]
    )
    response = completion.choices[0].message.content
    st.write(f"**הבוט:** {response}")
