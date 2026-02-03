import streamlit as st
from groq import Groq
import psycopg2
import pandas as pd

# --- הגדרות ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
DB_URL = st.secrets["DB_URL"] # וודא שב-Secrets של Streamlit מופיע ה-URL מ-Neon
client = Groq(api_key=GROQ_API_KEY)

# פונקציה עם CACHE למהירות מקסימלית
@st.cache_data(ttl=300) 
def get_inventory():
    try:
        conn = psycopg2.connect(DB_URL)
        query = "SELECT name, price, stock FROM products"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_string(index=False)
    except Exception as e:
        return "המלאי לא זמין כרגע."

# לוגיקה עבור הממשק וה-Make
inventory_data = get_inventory()

# שים לב לשינוי המודל כאן - זה התיקון לשגיאה שלך!
def get_ai_response(user_input):
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[
            {"role": "system", "content": f"עוזר במכולת. מלאי:\n{inventory_data}"},
            {"role": "user", "content": user_input}
        ]
    )
    return completion.choices[0].message.content

# בדיקת פרמטרים מ-Make
if "message" in st.query_params:
    reply = get_ai_response(st.query_params["message"])
    st.write(reply)
    st.stop()

# ממשק האתר
st.title("ניהול מכולת - Neon + Groq")
user_text = st.text_input("נסה את הבוט:")
if user_text:
    st.write(get_ai_response(user_text))
