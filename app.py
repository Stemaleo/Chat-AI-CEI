import streamlit as st
import pandas as pd
import plotly.express as px
from src.agent import analyze_intent_and_execute

st.set_page_config(page_title="Election Results Chat", layout="wide")

st.title("🗳️ Chat with 2025 Côte d'Ivoire Election Data")
st.markdown("Ask questions, compute aggregations, or request charts based on the official PDF dataset.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your AI assistant for the 2025 election results. What would you like to know?"}
    ]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.markdown(message["content"])
            if "data" in message:
                if isinstance(message["data"], pd.DataFrame):
                    st.dataframe(message["data"])
            if "chart" in message:
                st.plotly_chart(message["chart"], use_container_width=True)
        else:
            st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("E.g., How many seats did RHDP win? or Show a pie chart of top 5 candidates in region X"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Analyzing data..."):
        response = analyze_intent_and_execute(prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response["text"])
            
            new_msg = {"role": "assistant", "content": response["text"]}
            
            if response["type"] == "answer":
                if not response["data"].empty:
                    st.dataframe(response["data"])
                    new_msg["data"] = response["data"]
            
            elif response["type"] == "chart":
                df = response["data"]
                if not df.empty and len(df.columns) >= 2:
                    # Very simple heuristic: use the first column as X/labels, second as Y/values
                    x_col = df.columns[0]
                    y_col = df.columns[1]
                    
                    if "pie" in prompt.lower():
                        fig = px.pie(df, names=x_col, values=y_col, title=f"{y_col} by {x_col}")
                    else:
                        fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
                        
                    st.plotly_chart(fig, use_container_width=True)
                    new_msg["chart"] = fig
                else:
                    st.warning("Not enough data to draw a chart.")
                    
            st.session_state.messages.append(new_msg)
