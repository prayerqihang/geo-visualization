import json
import streamlit as st


def load_lottie_file(filepath: str):
    """从指定路径加载 Lottie JSON 文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Lottie 文件未找到: {filepath}")
        return None
