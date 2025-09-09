import streamlit as st
import pandas as pd
import psycopg2
import os
import requests
import uuid

st.set_page_config(page_title="Pending GUID Viewer", layout="wide")
st.title("📊 Danh sách bài viết `pending`")

# Kết nối DB (trùng tên service trong Docker Compose)
conn1 = psycopg2.connect(
    host="postgres",
    dbname="postgres",
    user=os.getenv("PG_USER"),
    password=os.getenv("PG_PASS"),
)

query1 = "SELECT guid, link, iso_date FROM public.articles_status WHERE status = 'pending';"
df1 = pd.read_sql(query1, conn1)
#conn1.close()

st.dataframe(df1, use_container_width=True)

st.title("📊 Danh sách bài viết `completed`")

# Kết nối DB (trùng tên service trong Docker Compose)

query2 = "SELECT * FROM public.articles_index limit 20;"
df2 = pd.read_sql(query2, conn1)
conn1.close()

st.dataframe(df2, use_container_width=True)

# Constants
st.title("💬 KietCorn Chatbot")

# Lưu lịch sử hội thoại
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Hiển thị lịch sử
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Nhập tin nhắn người dùng
if prompt := st.chat_input("Type your question about lead generation..."):
    # Lưu tin nhắn user
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gửi tới webhook n8n
    webhook_url = "http://10.4.21.3:5678/webhook/invoke_agent"
    try:
        response = requests.post(webhook_url, json={"query": prompt})

        if response.status_code == 200:
            try:
                result = response.json()
                ai_reply = result.get("reply") or str(result)  # fallback
            except Exception:
                ai_reply = response.text  # nếu không parse được JSON thì lấy text

            # Lưu tin nhắn bot
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            with st.chat_message("assistant"):
                st.markdown(ai_reply)

        else:
            error_msg = f"❌ Request failed: {response.status_code}"
            st.session_state["messages"].append({"role": "assistant", "content": error_msg})
            with st.chat_message("assistant"):
                st.error(error_msg)

    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        st.session_state["messages"].append({"role": "assistant", "content": error_msg})
        with st.chat_message("assistant"):
            st.error(error_msg)
