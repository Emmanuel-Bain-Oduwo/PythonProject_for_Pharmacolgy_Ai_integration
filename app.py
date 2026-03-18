
"""Compatibility launcher.

Use this file as an alternate entrypoint:
    streamlit run app.py

It delegates to the maintained app implementation in `app_main_pharma.py`.
"""

import streamlit as st

if "startup_done" not in st.session_state:
    import startup
    startup.main()
    st.session_state.startup_done = True

from app_main_pharma import *  # noqa: F401,F403
