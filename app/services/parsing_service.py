from __future__ import annotations

import re
from datetime import date
from typing import Any

from rapidfuzz import fuzz

from app.models import DocumentType, ValidationStatus
from app.utils.validators import is_valid_curp, normalize_text, parse_date_safe, split_full_name


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
        full_name, first_name, last_name = self._extract_ine_name(raw_text)
        birth_date = self._extract_ine_birth_date(raw_text)
        sex = self._extract_sex(raw_text)
        national_id = self._extract_ine_national_id(raw_text)
        curp = self._extract_ine_curp(raw_text)
        if not birth_date:
            birth_date = self._extract_birth_date_from_curp_candidate(raw_text)
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

    def _extract_ine_name(self, raw_text: str) -> tuple[str | None, str | None, str | None]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        label_index = self._find_line_index_by_keywords(lines, ["NOMBRE", "NOMBRE", "NOMBRES"])

        candidate_lines: list[str] = []
        if label_index is not None:
            candidate_lines = self._collect_name_block_after_label(lines, label_index)

        if not candidate_lines or len(candidate_lines) < 2:
            candidate_lines = self._collect_name_block_before_context(lines)

        if not candidate_lines or len(candidate_lines) < 2:
            candidate_lines = self._collect_name_block_around_sex_context(lines)

        if not candidate_lines:
            fallback_name = self._extract_best_name_candidate(lines)
            if not fallback_name:
                return None, None, None
            first_name, last_name = split_full_name(fallback_name)
            return fallback_name, first_name, last_name

        full_name = " ".join(candidate_lines).strip() or None
        if not full_name:
            return None, None, None

        if len(candidate_lines) >= 2:
            last_name = " ".join(candidate_lines[:-1]).strip() or None
            first_name = candidate_lines[-1].strip() or None
            return full_name, first_name, last_name

        first_name, last_name = split_full_name(full_name)
        return full_name, first_name, last_name

    def _extract_ine_birth_date(self, raw_text: str) -> date | None:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        label_index = self._find_line_index_by_keywords(lines, ["NACIMIENTO", "FECHA DE NACIMIENTO", "F NAC"])

        candidate_lines: list[str] = []
        if label_index is not None:
            candidate_lines.append(lines[label_index])
            if label_index + 1 < len(lines):
                candidate_lines.append(lines[label_index + 1])

        candidate_lines.extend(lines)

        for line in candidate_lines:
            for candidate in self._extract_date_candidates(line):
                parsed = parse_date_safe(candidate)
                if parsed:
                    return parsed

        return self._extract_first_date(raw_text)

    def _extract_ine_national_id(self, raw_text: str) -> str | None:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        label_index = self._find_line_index_by_keywords(lines, ["FOLIO", "FOLIO NACIONAL", "CIC"])

        if label_index is not None:
            line = lines[label_index]
            match = re.search(r"\b\d{13}\b", line.replace(" ", ""))
            if match:
                return match.group(0)

        return self._extract_regex(raw_text, r"\b\d{13}\b")

    def _extract_ine_curp(self, raw_text: str) -> str | None:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        label_index = self._find_line_index_by_keywords(lines, ["CURP"])
        candidate_lines: list[str] = []

        if label_index is not None:
            candidate_lines.append(lines[label_index])
            if label_index + 1 < len(lines):
                candidate_lines.append(lines[label_index + 1])

        candidate_lines.extend(lines)

        for line in candidate_lines:
            prepared_line = self._prepare_curp_line(line)
            tokens = re.findall(r"[A-Z0-9]{10,20}", prepared_line.replace(" ", ""))
            for token in tokens:
                normalized = self._normalize_curp_candidate(token)
                if normalized and is_valid_curp(normalized):
                    return normalized

        return None

    def _extract_birth_date_from_curp_candidate(self, raw_text: str) -> date | None:
        for line in [line.strip() for line in raw_text.splitlines() if line.strip()]:
            normalized_line = self._prepare_curp_line(line)
            for token in re.findall(r"[A-Z0-9]{10,20}", normalized_line.replace(" ", "")):
                if len(token) < 18:
                    continue
                for start_idx in range(0, len(token) - 17):
                    normalized = self._normalize_curp_candidate(token[start_idx : start_idx + 18])
                    if not normalized or len(normalized) != 18:
                        continue
                    date_candidate = normalized[4:10]
                    parsed = self._parse_mrz_date(date_candidate)
                    if parsed:
                        return parsed
        return None

    @staticmethod
    def _prepare_curp_line(line: str) -> str:
        normalized_line = normalize_text(line)
        normalized_line = re.sub(r"^(CURP|CURE|CURF)\s*", "", normalized_line)
        return normalized_line

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
    def _extract_date_candidates(text: str) -> list[str]:
        normalized = normalize_text(text)
        return re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b|\b\d{2}\s+\d{2}\s+\d{2,4}\b|\b\d{8}\b", normalized)

    @staticmethod
    def _extract_first_date(raw_text: str) -> date | None:
        candidates = re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b|\b\d{2}\s+\d{2}\s+\d{2,4}\b|\b\d{8}\b", raw_text)
        for candidate in candidates:
            parsed = parse_date_safe(candidate)
            if parsed:
                return parsed
        return None

    @staticmethod
    def _extract_last_date(raw_text: str) -> date | None:
        candidates = re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b|\b\d{2}\s+\d{2}\s+\d{2,4}\b|\b\d{8}\b", raw_text)
        for candidate in reversed(candidates):
            parsed = parse_date_safe(candidate, allow_future=True)
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

    @classmethod
    def _find_line_index_by_keywords(cls, lines: list[str], keywords: list[str], threshold: int = 78) -> int | None:
        for idx, line in enumerate(lines):
            normalized_line = normalize_text(line)
            compact_line = normalized_line.replace(" ", "")
            dynamic_threshold = threshold
            if len(compact_line) <= 10:
                dynamic_threshold = min(dynamic_threshold, 62)
            for keyword in keywords:
                normalized_keyword = normalize_text(keyword)
                if normalized_keyword in normalized_line or normalized_keyword.replace(" ", "") in compact_line:
                    return idx
                if fuzz.partial_ratio(normalized_keyword, normalized_line) >= dynamic_threshold:
                    return idx
                if fuzz.partial_ratio(normalized_keyword.replace(" ", ""), compact_line) >= dynamic_threshold:
                    return idx
                if fuzz.ratio(normalized_keyword.replace(" ", ""), compact_line) >= dynamic_threshold:
                    return idx
        return None

    @classmethod
    def _collect_name_block_after_label(cls, lines: list[str], label_index: int) -> list[str]:
        candidates: list[str] = []
        for line in lines[label_index + 1 : label_index + 5]:
            if cls._is_stop_line_for_ine_name(line):
                break
            cleaned = cls._clean_ine_name_line(line, allow_single_token=True)
            if cleaned:
                candidates.append(cleaned)
        return candidates

    @classmethod
    def _collect_name_block_before_context(cls, lines: list[str]) -> list[str]:
        context_index = cls._find_line_index_by_keywords(
            lines,
            ["SEXO", "SEX", "NACIMIENTO", "DOMICILIO", "CURP", "CLAVE DE ELECTOR"],
            threshold=74,
        )
        if context_index is None:
            return []

        candidates: list[str] = []
        start_index = max(0, context_index - 4)
        for line in lines[start_index:context_index]:
            if cls._is_stop_line_for_ine_name(line):
                candidates.clear()
                continue
            cleaned = cls._clean_ine_name_line(line, allow_single_token=True)
            if cleaned:
                candidates.append(cleaned)

        while len(candidates) > 3:
            candidates.pop(0)

        return candidates

    @classmethod
    def _collect_name_block_around_sex_context(cls, lines: list[str]) -> list[str]:
        sex_index = cls._find_line_index_by_keywords(lines, ["SEXO", "SEX", "SEO"], threshold=60)
        if sex_index is None:
            return []

        candidates: list[str] = []
        for idx in range(max(0, sex_index - 2), min(len(lines), sex_index + 2)):
            line = lines[idx]
            if cls._is_stop_line_for_ine_name(line):
                continue
            cleaned = cls._clean_ine_name_line(line, allow_single_token=True)
            if cleaned:
                candidates.append(cleaned)

        deduped: list[str] = []
        for candidate in candidates:
            if candidate not in deduped:
                deduped.append(candidate)

        return deduped

    @classmethod
    def _extract_best_name_candidate(cls, lines: list[str]) -> str | None:
        scored_candidates: list[tuple[float, str]] = []
        for idx, line in enumerate(lines[:10]):
            if cls._is_stop_line_for_ine_name(line):
                continue
            cleaned = cls._clean_ine_name_line(line)
            if not cleaned:
                continue

            tokens = cleaned.split()
            letter_count = sum(1 for char in cleaned if char.isalpha())
            score = float(letter_count) + (len(tokens) * 8) - (idx * 2)
            if len(tokens) >= 2:
                score += 12
            if any(token in {"DE", "DEL", "LA", "LAS", "LOS"} for token in tokens):
                score += 3
            scored_candidates.append((score, cleaned))

        if not scored_candidates:
            return None

        return max(scored_candidates, key=lambda item: item[0])[1]

    @classmethod
    def _clean_ine_name_line(cls, line: str, *, allow_single_token: bool = False) -> str | None:
        normalized = normalize_text(line)
        normalized = re.sub(r"\b(NOMBRE|NOMBRE|NOMBRES)\b", " ", normalized)
        normalized = re.sub(r"\b(SEXO|SEX|SEO|HOMBRE|MUJER)\b.*$", " ", normalized)
        normalized = re.sub(r"[^A-Z0-9 ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            return None

        tokens: list[str] = []
        for token in normalized.split():
            candidate = cls._clean_ine_name_token(token)
            if candidate:
                tokens.extend(candidate)

        if len(tokens) < 2 and not allow_single_token:
            return None

        if not tokens:
            return None

        return " ".join(tokens).strip() or None

    @staticmethod
    def _clean_ine_name_token(token: str) -> list[str]:
        if token.isdigit():
            return []

        candidate = token.translate(str.maketrans({"0": "O", "1": "I", "5": "S"}))
        if re.search(r"\d", candidate):
            return []

        ignored_tokens = {
            "INSTITUTO",
            "FEDERAL",
            "ELECTORAL",
            "REGISTRO",
            "ELECTORES",
            "CREDENCIAL",
            "VOTAR",
            "DOMICILIO",
            "DIRECCION",
            "CURP",
            "FOLIO",
            "CLAVE",
            "ELECTOR",
            "SECCION",
            "VIGENCIA",
            "ANO",
            "NACIMIENTO",
            "FECHA",
            "COL",
            "CALLE",
            "MUNICIPIO",
            "ESTADO",
            "LOCALIDAD",
            "SEXO",
            "H",
            "M",
            "NOVENE",
        }
        if candidate in ignored_tokens:
            return []

        if candidate.startswith("DE") and len(candidate) > 4 and candidate not in {"DEL", "DESDE"}:
            return ["DE", candidate[2:]]

        if len(candidate) == 1 and candidate not in {"Y"}:
            return []

        return [candidate]

    @classmethod
    def _is_stop_line_for_ine_name(cls, line: str) -> bool:
        normalized = normalize_text(line)
        stop_keywords = [
            "DOMICILIO",
            "DIRECCION",
            "DOMOLO",
            "DOMIC",
            "CURP",
            "CLAVE DE ELECTOR",
            "CLAVE",
            "ELECTOR",
            "SECCION",
            "VIGENCIA",
            "ANO DE REGISTRO",
            "NACIMIENTO",
            "FECHA",
            "FOLIO",
            "INSTITUTO",
            "REGISTRO FEDERAL",
            "CREDENCIAL PARA VOTAR",
            "MUNICIPIO",
            "ESTADO",
            "LOCALIDAD",
            "DOMIC",
        ]
        if any(keyword in normalized for keyword in stop_keywords):
            return True
        if normalized.startswith(("DOM", "C ", "COL ", "CALLE ", "AV ", "AVE ")):
            return True
        if re.search(r"\b(COL|CP|C P|DF)\b", normalized):
            return True
        return any(fuzz.partial_ratio(normalize_text(keyword), normalized) >= 82 for keyword in stop_keywords)

    @staticmethod
    def _normalize_curp_candidate(candidate: str) -> str | None:
        compact = normalize_text(candidate).replace(" ", "")
        if len(compact) != 18:
            return None

        letters_positions = {0, 1, 2, 3, 10, 11, 12, 13, 14, 15}
        digits_positions = {4, 5, 6, 7, 8, 9, 17}

        normalized_chars: list[str] = []
        for idx, char in enumerate(compact):
            if idx in letters_positions:
                normalized_chars.append({"0": "O", "1": "I", "5": "S", "8": "B"}.get(char, char))
                continue
            if idx in digits_positions:
                normalized_chars.append({"O": "0", "Q": "0", "I": "1", "L": "1", "S": "5", "B": "8"}.get(char, char))
                continue
            if idx == 16:
                normalized_chars.append({"O": "0", "Q": "0"}.get(char, char))
                continue
            normalized_chars.append(char)

        return "".join(normalized_chars)
