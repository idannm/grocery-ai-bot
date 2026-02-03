import streamlit as st
import psycopg2
import pandas as pd
from groq import Groq

# --- הגדרות ---
# שים לב לעדכן את המפתחות שלך כאן!
# במקום לשים את המפתח האמיתי, אנחנו כותבים את זה ככה:
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
DB_URL = st.secrets["DB_URL"]
ADMIN_PASSWORD = "1234" 

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
        return f"המלאי לא זמין כרגע: {e}"

# --- הגדרות דף ---
st.set_page_config(page_title="המכולת החכמה", layout="wide")

# ניהול זיכרון השיחה
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- תפריט צד (ניהול) ---
with st.sidebar:
    st.title("🛠️ לוח בקרה")
    show_admin = st.checkbox("כניסת מנהל")
    if show_admin:
        pwd = st.text_input("סיסמה", type="password")
        if pwd == ADMIN_PASSWORD:
            st.success("מחובר כמנהל")
            admin_tab = st.radio("פעולות:", ["עריכת מוצרים", "הגדרות"])
            
            if admin_tab == "עריכת מוצרים":
                try:
                    conn = get_db_connection()
                    df = pd.read_sql_query("SELECT * FROM products ORDER BY id", conn)
                    edited_df = st.data_editor(df, num_rows="dynamic", key="data_editor")
                    if st.button("שמור שינויים"):
                        cur = conn.cursor()
                        for _, row in edited_df.iterrows():
                            cur.execute("UPDATE products SET name=%s, price=%s, stock=%s WHERE id=%s", 
                                       (row['name'], row['price'], row['stock'], row['id']))
                        conn.commit()
                        cur.close()
                        st.success("המחסן עודכן!")
                    conn.close()
                except Exception as e:
                    st.error(f"שגיאה בגישה לבסיס הנתונים: {e}")
        else:
            st.info("הכנס סיסמה כדי לראות הגדרות")

# --- גוף האפליקציה (צ'אט לקוחות) ---
st.title("🛒 המכולת של החבר'ה")

# הצגת היסטוריית השיחה
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# קלט מהלקוח
if prompt := st.chat_input("אהלן! מה אפשר להביא לך היום?"):
    # הוספת הודעת המשתמש לזיכרון
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # יצירת תשובת הבוט
    with st.chat_message("assistant"):
        inventory_data = get_inventory()
        
        # בניית ה-Prompt בצורה בטוחה
        system_msg = f"אתה עוזר במכולת שכונתית וחברית. המלאי שלך:\n{inventory_data}\n\n"
        system_msg += "הוראות: אל תהיה רשמי! אל תגיד 'אדוני'. השתמש בשמות חיבה כמו 'צדיק', 'נשמה', 'אלוף'. "
        system_msg += "לפני סגירת הזמנה, חובה לבקש: שם מלא, כתובת וטלפון. אל תאשר בלי זה."

        # הכנת ההיסטוריה לשליחה ל-AI
        full_history = [{"role": "system", "content": system_msg}] + st.session_state.messages

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=full_history
            )
            
            ai_answer = response.choices[0].message.content
            st.markdown(ai_answer)
            st.session_state.messages.append({"role": "assistant", "content": ai_answer})
        except Exception as e:
            st.error(f"שגיאה בתקשורת עם ה-AI: {e}")

# כפתור איפוס שיחה בתפריט הצד
if st.sidebar.button("🗑️ נקה שיחה"):
    st.session_state.messages = []
    st.rerun()
