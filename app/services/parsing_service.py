from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

from app.models import DocumentType, ValidationStatus
from app.utils.validators import is_valid_curp, parse_date_safe, split_full_name


class ParsingService:
    def parse_document(self, *, document_type: DocumentType, raw_text: str) -> dict[str, Any]:
        normalized_text = self._prepare_text(raw_text)
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
        full_name = self._extract_name_like_value(
            raw_text,
            labels=[r"NOMBRE", r"NOMBRE\(S\)"],
        )
        if not full_name:
            full_name = self._extract_name_line(raw_text)
        first_name, last_name = split_full_name(full_name)
        birth_date = self._extract_first_date(raw_text)
        sex = self._extract_sex(raw_text)
        national_id = self._extract_regex(raw_text, r"\b\d{13}\b")
        curp = self._extract_regex(raw_text, r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b")
        document_number = self._extract_preferred_numeric_id(raw_text, preferred_lengths=(13, 12, 11, 10, 9))
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
        mrz_lines = self._extract_mrz_lines(raw_text)
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
            mrz_parsed = self._parse_passport_mrz(line_one, line_two)
            full_name = mrz_parsed["full_name"]
            first_name = mrz_parsed["first_name"]
            last_name = mrz_parsed["last_name"]
            birth_date = mrz_parsed["birth_date"]
            sex = mrz_parsed["sex"]
            document_number = mrz_parsed["document_number"]
            nationality = mrz_parsed["nationality"]
            expiration_date = mrz_parsed["expiration_date"]

        if not full_name:
            full_name = self._extract_name_like_value(raw_text, [r"NOMBRE", r"NAME", r"APELLIDOS Y NOMBRES"])
            if not full_name:
                full_name = self._extract_name_line(raw_text)
            first_name, last_name = split_full_name(full_name)

        if not birth_date:
            birth_date = self._extract_first_date(raw_text)
        if not sex:
            sex = self._extract_sex(raw_text)
        if not document_number:
            document_number = self._extract_passport_number(raw_text)
        if not nationality:
            nationality = self._extract_labeled_value(raw_text, [r"NACIONALIDAD", r"NATIONALITY"])
        if not expiration_date:
            expiration_date = self._extract_last_date(raw_text)

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
        full_name = self._extract_name_like_value(
            raw_text,
            [r"APELLIDOS Y NOMBRES", r"NOMBRES Y APELLIDOS", r"NOMBRES", r"APELLIDOS"],
        )
        if not full_name:
            full_name = self._extract_name_line(raw_text)
        first_name, last_name = split_full_name(full_name)
        birth_date = self._extract_first_date(raw_text)
        sex = self._extract_sex(raw_text)
        national_id = self._extract_labeled_or_numeric_id(raw_text, [r"NUMERO", r"IDENTIFICACION", r"CEDULA"])
        document_number = national_id

        dates = self._extract_all_dates(raw_text)
        issue_date = dates[1] if len(dates) > 1 else None

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
            "issue_date": issue_date,
            "expiration_date": None,
        }

    @staticmethod
    def _prepare_text(raw_text: str) -> str:
        normalized = unicodedata.normalize("NFKC", raw_text.replace("\r", "\n"))
        normalized = normalized.replace("\t", " ")
        normalized = re.sub(r"[ ]{2,}", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    @staticmethod
    def _normalized_lines(raw_text: str) -> list[str]:
        return [re.sub(r"\s+", " ", line).strip() for line in raw_text.splitlines() if line.strip()]

    def _extract_name_line(self, raw_text: str) -> str | None:
        for line in self._normalized_lines(raw_text):
            compact = self._accentless_upper(line)
            if any(token in compact for token in ("REPUBLICA", "IDENTIFICACION", "PASAPORTE", "NATIONALITY", "DOMICILIO")):
                continue
            if re.fullmatch(r"[A-ZÁÉÍÓÚÑ ]{6,}", line, flags=re.IGNORECASE):
                cleaned = self._clean_name(line)
                if cleaned and len(cleaned.split()) >= 2:
                    return cleaned
        return None

    def _extract_name_like_value(self, raw_text: str, labels: list[str]) -> str | None:
        value = self._extract_labeled_value(raw_text, labels)
        return self._clean_name(value)

    def _extract_labeled_or_numeric_id(self, raw_text: str, labels: list[str]) -> str | None:
        candidate = self._extract_labeled_value(raw_text, labels)
        if candidate:
            match = re.search(r"\b\d{6,12}\b", candidate)
            if match:
                return match.group(0)
        return self._extract_preferred_numeric_id(raw_text, preferred_lengths=(10, 9, 8, 7, 6, 11, 12))

    def _extract_preferred_numeric_id(self, raw_text: str, preferred_lengths: tuple[int, ...]) -> str | None:
        candidates = re.findall(r"\b\d{6,13}\b", raw_text.replace("\n", " "))
        if not candidates:
            return None
        for target_length in preferred_lengths:
            for candidate in candidates:
                if len(candidate) == target_length:
                    return candidate
        return max(candidates, key=len)

    def _extract_passport_number(self, raw_text: str) -> str | None:
        labeled = self._extract_labeled_value(raw_text, [r"PASSPORT NO", r"PASAPORTE NO", r"NO\. PASAPORTE", r"DOCUMENT NO"])
        if labeled:
            match = re.search(r"\b[A-Z0-9]{6,12}\b", self._accentless_upper(labeled))
            if match:
                return match.group(0)
        return self._extract_regex(self._accentless_upper(raw_text), r"\b[A-Z]{1,3}\d{6,9}\b|\b[A-Z0-9]{6,12}\b")

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

    def _extract_mrz_lines(self, raw_text: str) -> list[str]:
        lines = []
        for line in self._normalized_lines(raw_text):
            compact = line.replace(" ", "")
            if "<" in compact and len(compact) >= 20:
                lines.append(compact)
        return lines

    def _parse_passport_mrz(self, line_one: str, line_two: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "full_name": None,
            "first_name": None,
            "last_name": None,
            "birth_date": None,
            "sex": None,
            "document_number": None,
            "nationality": None,
            "expiration_date": None,
        }
        if not line_one.startswith("P<"):
            return result

        nationality = line_one[2:5].replace("<", "") or None
        name_section = line_one[5:]
        name_parts = [part.replace("<", " ").strip() for part in name_section.split("<<") if part.strip("<")]
        last_name = name_parts[0] if name_parts else None
        first_name = " ".join(name_parts[1:]).strip() or None
        full_name = " ".join(part for part in [first_name, last_name] if part) or None

        if len(line_two) >= 27:
            document_number = line_two[0:9].replace("<", "") or None
            birth_date = self._parse_mrz_date(line_two[13:19])
            sex = line_two[20].replace("<", "") or None
            expiration_date = self._parse_mrz_date(line_two[21:27])
        else:
            document_number = None
            birth_date = None
            sex = None
            expiration_date = None

        result.update(
            {
                "full_name": self._clean_name(full_name),
                "first_name": self._clean_name(first_name),
                "last_name": self._clean_name(last_name),
                "birth_date": birth_date,
                "sex": self._normalize_sex_value(sex),
                "document_number": document_number,
                "nationality": nationality,
                "expiration_date": expiration_date,
            }
        )
        return result

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
    def _extract_all_dates(raw_text: str) -> list[date]:
        candidates = re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b|\b\d{8}\b", raw_text)
        parsed_dates: list[date] = []
        for candidate in candidates:
            parsed = parse_date_safe(candidate)
            if parsed and parsed not in parsed_dates:
                parsed_dates.append(parsed)
        return parsed_dates

    def _extract_sex(self, raw_text: str) -> str | None:
        normalized = self._accentless_upper(raw_text)
        labeled = re.search(r"(?:SEXO|SEX)\s*[: ]\s*(MASCULINO|FEMENINO|HOMBRE|MUJER|M|F|H)", normalized)
        if labeled:
            return self._normalize_sex_value(labeled.group(1))
        match = re.search(r"\b(MASCULINO|FEMENINO|HOMBRE|MUJER|M|F|H)\b", normalized)
        if match:
            return self._normalize_sex_value(match.group(1))
        return None

    @staticmethod
    def _normalize_sex_value(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().upper()
        if normalized in {"MASCULINO", "HOMBRE", "H"}:
            return "M"
        if normalized in {"FEMENINO", "MUJER"}:
            return "F"
        if normalized in {"M", "F"}:
            return normalized
        return normalized

    @staticmethod
    def _clean_name(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"[^A-ZÁÉÍÓÚÑÜa-záéíóúñü< ]+", " ", value.replace("<", " "))
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or None

    @staticmethod
    def _accentless_upper(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(char for char in normalized if not unicodedata.combining(char)).upper()

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
