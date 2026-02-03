import streamlit as st
from groq import Groq
import psycopg2
import pandas as pd

# --- עיצוב האפליקציה ---
st.set_page_config(page_title="ניהול המכולת החכמה", layout="wide")

# --- הגדרות בסיסיות מה-Secrets ---
DB_URL = st.secrets["DB_URL"]

# --- Sidebar לניהול מפתחות ואבטחה ---
with st.sidebar:
    st.title("⚙️ הגדרות ניהול")
    custom_key = st.text_input("הזן מפתח Groq לניהול אישי:", type="password")
    api_key = custom_key if custom_key else st.secrets.get("GROQ_API_KEY", "")
    
    if not api_key:
        st.warning("נא להזין מפתח API כדי להפעיל את הבינה.")

client = Groq(api_key=api_key) if api_key else None

# --- פונקציות Database (Neon.tech) ---
def get_db_connection():
    return psycopg2.connect(DB_URL)

def get_inventory():
    try:
        conn = get_db_connection()
        query = "SELECT id, name, price, stock FROM products ORDER BY name ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"שגיאה בחיבור למסד הנתונים: {e}")
        return pd.DataFrame()

def update_db(query, params):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        st.success("הנתונים עודכנו בהצלחה!")
        st.cache_data.clear() # ניקוי הזיכרון כדי שיראו את השינוי מיד
    except Exception as e:
        st.error(f"שגיאה בעדכון: {e}")

# --- לוגיקה עבור ה-AI (וואטסאפ ובדיקה) ---
inventory_df = get_inventory()
inventory_text = inventory_df.to_string(index=False)

def ask_ai(user_query):
    if not client: return "מפתח API לא הוגדר."
    
    system_prompt = f"""
    אתה עוזר במכולת חכמה. המלאי המעודכן הוא:
    {inventory_text}
    
    הנחיות חשובות:
    1. אם לקוח מבקש מוצר שלא מופיע ברשימה, תגיד בנימוס ש"המוצר לא קיים כרגע במלאי".
    2. אם המוצר קיים אבל ה-stock הוא 0, תגיד ש"כרגע אזל מהמלאי, נחזור להביא בקרוב".
    3. תהיה חביב, השתמש בשפה של 'צדיק' ו'אחי'. 
    4. בסיום הזמנה, תמיד בקש שם וכתובת למשלוח.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    )
    return completion.choices[0].message.content

# --- בדיקת בקשה מ-Make (וואטסאפ) ---
if "message" in st.query_params:
    st.write(ask_ai(st.query_params["message"]))
    st.stop()

# --- ממשק המשתמש (UI) ---
tab1, tab2, tab3 = st.tabs(["🤖 צ'אט בדיקה", "📦 ניהול מלאי", "📝 הזמנות"])

with tab1:
    st.header("בדיקת הבינה המלאכותית")
    u_input = st.text_input("שאל את הבוט (למשל: 'יש חלב?'):")
    if u_input:
        with st.spinner("הבוט חושב..."):
            st.chat_message("assistant").write(ask_ai(u_input))

with tab2:
    st.header("ניהול מוצרים במכולת")
    
    # הצגת המלאי הקיים
    st.subheader("המלאי הנוכחי")
    st.dataframe(inventory_df, use_container_width=True)
    
    # טופס הוספת מוצר
    with st.expander("➕ הוספת מוצר חדש"):
        with st.form("add_form"):
            new_name = st.text_input("שם המוצר")
            new_price = st.number_input("מחיר", min_value=0.0)
            new_stock = st.number_input("כמות במלאי", min_value=0)
            if st.form_submit_button("הוסף למסד הנתונים"):
                update_db("INSERT INTO products (name, price, stock) VALUES (%s, %s, %s)", (new_name, new_price, new_stock))

    # מחיקת מוצר
    with st.expander("🗑️ מחיקת מוצר"):
        prod_id = st.number_input("הזן ID של מוצר למחיקה", min_value=1)
        if st.button("מחק מוצר"):
            update_db("DELETE FROM products WHERE id = %s", (prod_id,))

with tab3:
    st.header("הזמנות אחרונות")
    try:
        conn = get_db_connection()
        orders = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC LIMIT 20", conn)
        st.table(orders)
        conn.close()
    except:
        st.info("אין הזמנות חדשות להצגה.")
