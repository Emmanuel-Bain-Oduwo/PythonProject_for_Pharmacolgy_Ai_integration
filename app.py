
"""Compatibility launcher.

Use this file as an alternate entrypoint:
    streamlit run app.py

It delegates to the maintained app implementation in `app_main_pharma.py`.
"""

from app_main_pharma import *  # noqa: F401,F403
