"""Robust lab interpretation helpers.

This module provides resilient lab test matching with alias normalization,
case-insensitive lookup, and graceful fallback messages.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict

from db_config import DB_PATH


class LabInterpreter:
    _ALIASES = {
        "hb": "haemoglobin",
        "hemoglobin": "haemoglobin",
        "haemoglobin": "haemoglobin",
        "wbc": "white blood cell count",
        "white cell count": "white blood cell count",
        "platelet": "platelet count",
        "platelets": "platelet count",
        "plt": "platelet count",
        "creat": "creatinine",
        "scr": "creatinine",
        "bun": "blood urea nitrogen",
        "hba1c": "hba1c",
        "fbg": "glucose (fasting)",
        "glucose": "glucose (fasting)",
        "na": "sodium",
        "k": "potassium",
        "cl": "chloride",
        "hco3": "bicarbonate",
        "inr": "inr (international normalised ratio)",
        "ast": "aspartate aminotransferase",
        "alt": "alanine aminotransferase",
        "alp": "alkaline phosphatase",
        "ggt": "gamma-glutamyl transferase",
        "tsh": "thyroid stimulating hormone",
        "ft4": "free t4",
        "ft3": "free t3",
        "crp": "c-reactive protein",
    }

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    @classmethod
    def _norm(cls, value: str) -> str:
        return " ".join((value or "").strip().lower().replace("-", " ").replace("_", " ").split())

    def _lookup_ref(self, test_name: str):
        cur = self.conn.cursor()
        norm = self._norm(test_name)
        canonical = self._ALIASES.get(norm, norm)

        cur.execute(
            """
            SELECT * FROM lab_reference_ranges
            WHERE LOWER(test_name)=? OR LOWER(abbreviation)=?
            LIMIT 1
            """,
            (canonical, canonical),
        )
        ref = cur.fetchone()
        if ref:
            return ref

        like = f"%{canonical}%"
        cur.execute(
            """
            SELECT * FROM lab_reference_ranges
            WHERE LOWER(test_name) LIKE ? OR LOWER(abbreviation) LIKE ?
            ORDER BY CASE WHEN LOWER(test_name) LIKE ? THEN 0 ELSE 1 END, LENGTH(test_name)
            LIMIT 1
            """,
            (like, like, like),
        )
        return cur.fetchone()

    def interpret(self, test_name: str, value: float, gender: str = "male", age: int = 40) -> Dict[str, Any]:
        ref = self._lookup_ref(str(test_name))
        result: Dict[str, Any] = {"test": test_name, "value": value}
        if not ref:
            result["status"] = "⚠️ Reference range unavailable for this exact label"
            result["clinical_meaning"] = (
                "The test label could not be matched exactly. Verify naming (full test name or abbreviation), "
                "then re-check interpretation with local laboratory standards."
            )
            return result

        is_female = str(gender).strip().lower() == "female"
        lo = ref["min_adult_female"] if is_female else ref["min_adult_male"]
        hi = ref["max_adult_female"] if is_female else ref["max_adult_male"]
        if age < 18:
            lo, hi = ref["min_child"], ref["max_child"]
        if lo is None and hi is None:
            lo = ref["min_adult_female"] if is_female else ref["min_adult_male"]
            hi = ref["max_adult_female"] if is_female else ref["max_adult_male"]

        result["unit"] = ref["unit"]
        if lo is None and hi is None:
            rr = f"No fixed numeric range ({ref['unit']})"
        elif lo is None:
            rr = f"<= {hi} {ref['unit']}"
        elif hi is None:
            rr = f">= {lo} {ref['unit']}"
        else:
            rr = f"{lo} – {hi} {ref['unit']}"
        result["reference_range"] = rr

        crit_lo, crit_hi = ref["critical_low"], ref["critical_high"]
        if crit_lo is not None and value <= crit_lo:
            result["status"] = "🚨 CRITICAL LOW"
        elif crit_hi is not None and value >= crit_hi:
            result["status"] = "🚨 CRITICAL HIGH"
        elif lo is not None and value < lo:
            result["status"] = "🔴 LOW"
        elif hi is not None and value > hi:
            result["status"] = "🔴 HIGH"
        else:
            result["status"] = "✅ Normal"

        result["matched_reference"] = ref["test_name"]
        result["clinical_meaning"] = ref["clinical_meaning"]
        if ref["drug_effects"]:
            try:
                result["drugs_affecting_this_test"] = json.loads(ref["drug_effects"])
            except Exception:
                pass

        return result

