import streamlit as st
from groq import Groq
import psycopg2
import pandas as pd

# --- הגדרות ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
DB_URL = st.secrets["DB_URL"]
client = Groq(api_key=GROQ_API_KEY)

def get_db_connection():
    return psycopg2.connect(DB_URL)

@st.cache_data(ttl=600) # זה שומר את המלאי בזיכרון ל-10 דקות וחוסך זמן יקר!
def get_inventory():
    try:
        conn = get_db_connection()
        query = "SELECT name, price, stock FROM products"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except:
        return None
# --- לוגיקה עבור Make.com (וואטסאפ) ---
if "message" in st.query_params:
    user_msg = st.query_params["message"]
    inventory_df = get_inventory()
    inv_text = inventory_df.to_string(index=False) if inventory_df is not None else "אין מלאי"
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": f"אתה עוזר במכולת. מלאי:\n{inv_text}"},
                {"role": "user", "content": user_msg}
            ]
        )
        st.write(completion.choices[0].message.content)
        st.stop()
    except Exception as e:
        st.write(f"Error: {e}")
        st.stop()

# --- ממשק האפליקציה (למנהל) ---
st.set_page_config(page_title="ניהול מכולת", layout="wide")
st.sidebar.title("תפריט ניהול")
page = st.sidebar.radio("עבור אל:", ["צ'אט בדיקה", "ניהול מלאי", "הזמנות חדשות"])

if page == "צ'אט בדיקה":
    st.title("🤖 בדיקת הבוט")
    u_input = st.text_input("כתוב הודעה לבוט:")
    if u_input:
        # לוגיקת בדיקה דומה לוואטסאפ
        st.write("הבוט עונה...")

elif page == "ניהול מלאי":
    st.title("📦 ניהול מלאי")
    df = get_inventory()
    if df is not None:
        st.dataframe(df, use_container_width=True)
    else:
        st.error("לא ניתן לטעון מלאי")

elif page == "הזמנות חדשות":
    st.title("📝 הזמנות מהוואטסאפ")
    try:
        conn = get_db_connection()
        orders = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
        st.table(orders)
        conn.close()
    except:
        st.info("עדיין אין הזמנות במערכת.")
