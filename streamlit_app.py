import streamlit as st
import requests

st.set_page_config(
    page_title="AI Operations Intelligence Platform",
    page_icon="🛠️",
    layout="wide"
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.header("🛠️ Pending Actions")

    proposals = requests.get("http://127.0.0.1:8000/proposals").json()
    pending = [p for p in proposals if p["status"] == "pending"]

    if not pending:
        st.caption("No pending proposals right now.")

    for p in pending:
        with st.container(border=True):
            st.markdown(f"**{p['action']}** on `{p['pipeline_id']}`")
            st.caption(p["reason"])
            col1, col2 = st.columns(2)
            if col1.button("Approve", key=f"approve_{p['proposal_id']}"):
                requests.post(f"http://127.0.0.1:8000/proposals/{p['proposal_id']}/approve")
                st.rerun()
            if col2.button("Reject", key=f"reject_{p['proposal_id']}"):
                requests.post(f"http://127.0.0.1:8000/proposals/{p['proposal_id']}/reject")
                st.rerun()

    st.divider()
    if st.button("Start New Investigation"):
        requests.post("http://127.0.0.1:8000/reset")
        st.session_state.chat_history = []
        st.rerun()

st.title("AI Operations Intelligence Platform")

for role, text in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(text)

task = st.chat_input("What do you want to investigate?")

if task:
    st.session_state.chat_history.append(("user", task))
    with st.chat_message("user"):
        st.markdown(task)

    with st.chat_message("assistant"):
        with st.spinner("Investigating..."):
            response = requests.post(
                "http://127.0.0.1:8000/investigate",
                json={"task": task}
            )
            report = response.json()["report"]
        st.markdown(report)

    st.session_state.chat_history.append(("assistant", report))
    st.rerun()