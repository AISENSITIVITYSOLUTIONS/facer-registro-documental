from __future__ import annotations

from datetime import date
from typing import Any

from rapidfuzz import fuzz

from app.models import ComparisonStatus, User
from app.utils.validators import normalize_document_value, normalize_text


class ComparisonService:
    def compare_user_against_document(
        self,
        *,
        user: User,
        extracted_fields: dict[str, Any],
        registered_birth_date: date | None = None,
    ) -> dict[str, Any]:
        registered_first_name = normalize_text(user.first_name)
        registered_last_name = normalize_text(user.last_name)
        registered_full_name = normalize_text(f"{user.first_name} {user.last_name}")

        document_full_name = normalize_text(extracted_fields.get("full_name"))
        document_first_name = normalize_text(extracted_fields.get("first_name"))
        document_last_name = normalize_text(extracted_fields.get("last_name"))

        if not document_full_name:
            document_full_name = normalize_text(
                " ".join(part for part in [document_first_name, document_last_name] if part)
            )

        name_score = self._similarity_score(registered_full_name, document_full_name)
        first_name_score = self._similarity_score(registered_first_name, document_first_name)
        last_name_score = self._similarity_score(registered_last_name, document_last_name)
        birth_date_score = self._birth_date_score(registered_birth_date, extracted_fields.get("birth_date"))

        weights = {
            "name": 0.50,
            "first_name": 0.15,
            "last_name": 0.20,
            "birth_date": 0.15 if registered_birth_date else 0.0,
        }
        if not registered_birth_date:
            weights["name"] = 0.58
            weights["first_name"] = 0.17
            weights["last_name"] = 0.25

        weighted_score = round(
            (name_score * weights["name"])
            + (first_name_score * weights["first_name"])
            + (last_name_score * weights["last_name"])
            + (birth_date_score * weights["birth_date"]),
            4,
        )

        comparison_status = self._resolve_status(weighted_score)

        return {
            "comparison_score": weighted_score,
            "comparison_status": comparison_status.value,
            "comparison_breakdown": {
                "name_score": round(name_score, 4),
                "first_name_score": round(first_name_score, 4),
                "last_name_score": round(last_name_score, 4),
                "birth_date_score": round(birth_date_score, 4),
                "registered_name": registered_full_name,
                "document_name": document_full_name,
                "document_number": normalize_document_value(extracted_fields.get("document_number")),
            },
        }

    @staticmethod
    def _similarity_score(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return round(fuzz.token_sort_ratio(left, right) / 100.0, 4)

    @staticmethod
    def _birth_date_score(registered_birth_date: date | None, document_birth_date: date | None) -> float:
        if registered_birth_date is None or document_birth_date is None:
            return 0.0
        return 1.0 if registered_birth_date == document_birth_date else 0.0

    @staticmethod
    def _resolve_status(score: float) -> ComparisonStatus:
        if score >= 0.96:
            return ComparisonStatus.EXACT_MATCH
        if score >= 0.88:
            return ComparisonStatus.HIGH_MATCH
        if score >= 0.75:
            return ComparisonStatus.MEDIUM_MATCH
        if score >= 0.60:
            return ComparisonStatus.LOW_MATCH
        return ComparisonStatus.MISMATCH
