from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.models import DocumentType, ValidationStatus
from app.utils.validators import is_valid_curp, parse_date_safe, split_full_name


class ParsingService:
    def parse_document(self, *, document_type: DocumentType, raw_text: str) -> dict[str, Any]:
        normalized_text = raw_text.replace("\r", "\n")
        parser = {
            DocumentType.INE: self._parse_ine,
            DocumentType.PASSPORT_MX: self._parse_passport,
            DocumentType.CEDULA_CO: self._parse_cedula,
            DocumentType.PASSPORT_CO: self._parse_passport,
        }[document_type]
        extracted = parser(normalized_text)
        status = self._determine_validation_status(document_type=document_type, extracted=extracted)
        return {
            "fields": extracted,
            "validation_status": status.value,
        }

    def _parse_ine(self, raw_text: str) -> dict[str, Any]:
        full_name = self._extract_labeled_value(raw_text, [r"NOMBRE", r"NOMBRE\(S\)"])
        first_name, last_name = split_full_name(full_name)
        birth_date = self._extract_first_date(raw_text)
        sex = self._extract_sex(raw_text)
        national_id = self._extract_regex(raw_text, r"\b\d{13}\b")
        curp = self._extract_regex(raw_text, r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b")
        document_number = self._extract_regex(raw_text, r"\b\d{9,13}\b")
        expiration_date = self._extract_last_date(raw_text)

        return {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": birth_date,
            "sex": sex,
            "national_id": national_id,
            "document_number": document_number,
            "curp": curp if is_valid_curp(curp) else None,
            "nationality": "MEXICANA",
            "issue_date": None,
            "expiration_date": expiration_date,
        }

    def _parse_passport(self, raw_text: str) -> dict[str, Any]:
        mrz_lines = [line.replace(" ", "") for line in raw_text.splitlines() if "<" in line]
        full_name = None
        first_name = None
        last_name = None
        birth_date = None
        sex = None
        document_number = None
        nationality = None
        expiration_date = None

        if len(mrz_lines) >= 2:
            line_one = mrz_lines[-2]
            line_two = mrz_lines[-1]
            if line_one.startswith("P<"):
                nationality = line_one[2:5].replace("<", "") or None
                name_section = line_one[5:]
                name_parts = [part.replace("<", " ").strip() for part in name_section.split("<<")]
                if name_parts:
                    last_name = name_parts[0] or None
                    first_name = " ".join(name_parts[1:]).strip() or None
                    full_name = " ".join(part for part in [first_name, last_name] if part) or None
            if len(line_two) >= 27:
                document_number = line_two[0:9].replace("<", "") or None
                birth_date = self._parse_mrz_date(line_two[13:19])
                sex = line_two[20].replace("<", "") or None
                expiration_date = self._parse_mrz_date(line_two[21:27])

        if not full_name:
            full_name = self._extract_labeled_value(raw_text, [r"NOMBRE", r"NAME"])
            first_name, last_name = split_full_name(full_name)

        if not birth_date:
            birth_date = self._extract_first_date(raw_text)
        if not sex:
            sex = self._extract_sex(raw_text)
        if not document_number:
            document_number = self._extract_regex(raw_text, r"\b[A-Z0-9]{6,12}\b")
        if not nationality:
            nationality = self._extract_labeled_value(raw_text, [r"NACIONALIDAD", r"NATIONALITY"])

        return {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": birth_date,
            "sex": sex,
            "national_id": None,
            "document_number": document_number,
            "curp": None,
            "nationality": nationality,
            "issue_date": None,
            "expiration_date": expiration_date,
        }

    def _parse_cedula(self, raw_text: str) -> dict[str, Any]:
        full_name = self._extract_labeled_value(raw_text, [r"APELLIDOS Y NOMBRES", r"NOMBRES", r"APELLIDOS"])
        first_name, last_name = split_full_name(full_name)
        birth_date = self._extract_first_date(raw_text)
        sex = self._extract_sex(raw_text)
        national_id = self._extract_regex(raw_text, r"\b\d{6,12}\b")
        document_number = national_id

        return {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": birth_date,
            "sex": sex,
            "national_id": national_id,
            "document_number": document_number,
            "curp": None,
            "nationality": "COLOMBIANA",
            "issue_date": None,
            "expiration_date": None,
        }

    @staticmethod
    def _extract_labeled_value(raw_text: str, labels: list[str]) -> str | None:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            for label in labels:
                if re.search(label, line, flags=re.IGNORECASE):
                    cleaned = re.sub(label, "", line, flags=re.IGNORECASE).strip(" :")
                    if cleaned:
                        return cleaned
                    if idx + 1 < len(lines):
                        return lines[idx + 1]
        return None

    @staticmethod
    def _extract_regex(raw_text: str, pattern: str) -> str | None:
        match = re.search(pattern, raw_text.replace("\n", " "))
        return match.group(0) if match else None

    @staticmethod
    def _extract_first_date(raw_text: str) -> date | None:
        candidates = re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b|\b\d{8}\b", raw_text)
        for candidate in candidates:
            parsed = parse_date_safe(candidate)
            if parsed:
                return parsed
        return None

    @staticmethod
    def _extract_last_date(raw_text: str) -> date | None:
        candidates = re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b|\b\d{8}\b", raw_text)
        for candidate in reversed(candidates):
            parsed = parse_date_safe(candidate)
            if parsed:
                return parsed
        return None

    @staticmethod
    def _extract_sex(raw_text: str) -> str | None:
        match = re.search(r"\b(HOMBRE|MUJER|M|F|H)\b", raw_text, flags=re.IGNORECASE)
        return match.group(1).upper() if match else None

    @staticmethod
    def _parse_mrz_date(value: str) -> date | None:
        cleaned = value.strip().replace("<", "")
        if len(cleaned) != 6 or not cleaned.isdigit():
            return None
        year = int(cleaned[0:2])
        month = int(cleaned[2:4])
        day = int(cleaned[4:6])
        century = 1900 if year > 30 else 2000
        try:
            parsed = date(century + year, month, day)
        except ValueError:
            return None
        return parsed

    @staticmethod
    def _determine_validation_status(document_type: DocumentType, extracted: dict[str, Any]) -> ValidationStatus:
        required_fields = ["full_name", "birth_date"]
        if document_type in {DocumentType.INE, DocumentType.CEDULA_CO}:
            required_fields.append("national_id")
        else:
            required_fields.append("document_number")

        missing = [field for field in required_fields if not extracted.get(field)]
        if missing:
            return ValidationStatus.NEEDS_REVIEW
        return ValidationStatus.PENDING
