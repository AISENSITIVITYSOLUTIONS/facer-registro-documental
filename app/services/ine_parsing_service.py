"""
Specialized parsing service for Mexican INE (credencial de elector).

Extracts:
- nombre (first name / nombres)
- apellido_paterno
- apellido_materno
- nombre_completo (full name)
- nacionalidad
- fecha_nacimiento
- curp
- domicilio
- sexo
- clave_elector

Modern INE front layout (post-2014):
    NOMBRE
    <APELLIDO PATERNO>
    <APELLIDO MATERNO>
    <NOMBRE(S)>
    DOMICILIO
    ...

Older INE formats may have explicit APELLIDO PATERNO / APELLIDO MATERNO labels.
This parser handles both formats.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date
from typing import Any

from app.utils.validators import is_valid_curp, parse_date_safe

logger = logging.getLogger(__name__)

# Labels that signal the end of the name block
_STOP_LABELS = frozenset([
    "DOMICILIO", "CURP", "CLAVE", "SECCION", "VIGENCIA", "FECHA",
    "ESTADO", "MUNICIPIO", "EMISION", "LOCALIDAD", "AÑO",
    "NACIMIENTO", "REGISTRO", "SEXO", "NACIONALIDAD",
])

# Labels that signal the end of the address block
_ADDRESS_STOP_LABELS = frozenset([
    "CURP", "CLAVE", "SECCION", "VIGENCIA", "FECHA", "ESTADO",
    "MUNICIPIO", "EMISION", "LOCALIDAD", "AÑO", "REGISTRO",
])


class INEParsingService:
    """Parse OCR text from Mexican INE documents with high accuracy."""

    def parse(self, raw_text: str) -> dict[str, Any]:
        """Parse raw OCR text and extract INE fields."""
        normalized = self._prepare_text(raw_text)
        lines = self._get_lines(normalized)

        logger.info("INE Parser: %d lines to parse", len(lines))
        logger.debug("INE Parser lines: %s", lines)

        # Try modern format first (NOMBRE followed by 3 name lines)
        nombre, apellido_paterno, apellido_materno = self._extract_name_block(lines)

        # Fallback: try explicit labels (older INE format)
        if not apellido_paterno:
            apellido_paterno = self._extract_labeled_field(lines, [
                r"APELLIDO\s*PATERNO", r"AP\.?\s*PAT\.?",
            ])
        if not apellido_materno:
            apellido_materno = self._extract_labeled_field(lines, [
                r"APELLIDO\s*MATERNO", r"AP\.?\s*MAT\.?",
            ])
        if not nombre:
            nombre = self._extract_labeled_field(lines, [
                r"\bNOMBRE\(?S?\)?\b",
            ], skip_if_contains=["APELLIDO", "COMPLETO", "INSTITUTO", "ELECTORAL"])

        domicilio = self._extract_domicilio(lines)
        curp = self._extract_curp(normalized)
        fecha_nacimiento = self._extract_fecha_nacimiento(lines, normalized, curp)
        sexo = self._extract_sexo(lines, normalized, curp)
        nacionalidad = self._extract_nacionalidad(normalized)
        clave_elector = self._extract_clave_elector(normalized)

        # Build full name: "APELLIDO_PATERNO APELLIDO_MATERNO NOMBRE(S)"
        nombre_completo = self._build_full_name(apellido_paterno, apellido_materno, nombre)

        logger.info(
            "INE Parser result: nombre=%s, ap=%s, am=%s, full=%s, curp=%s",
            nombre, apellido_paterno, apellido_materno, nombre_completo, curp,
        )

        return {
            "nombre": nombre,
            "apellido_paterno": apellido_paterno,
            "apellido_materno": apellido_materno,
            "nombre_completo": nombre_completo,
            "nacionalidad": nacionalidad or "MEXICANA",
            "fecha_nacimiento": fecha_nacimiento,
            "curp": curp,
            "domicilio": domicilio,
            "sexo": sexo,
            "clave_elector": clave_elector,
            # Compatibility fields for the generic document system
            "full_name": nombre_completo,
            "first_name": nombre,
            "last_name": f"{apellido_paterno or ''} {apellido_materno or ''}".strip() or None,
            "birth_date": fecha_nacimiento,
            "sex": sexo,
            "national_id": clave_elector,
            "document_number": clave_elector,
            "nationality": nacionalidad or "MEXICANA",
            "issue_date": None,
            "expiration_date": None,
        }

    # ── Text Preparation ───────────────────────────────────────────────────

    @staticmethod
    def _prepare_text(raw_text: str) -> str:
        """Normalize text for consistent parsing."""
        normalized = unicodedata.normalize("NFKC", raw_text.replace("\r", "\n"))
        normalized = normalized.replace("\t", " ")
        normalized = re.sub(r"[ ]{2,}", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    @staticmethod
    def _get_lines(text: str) -> list[str]:
        """Get non-empty stripped lines."""
        return [line.strip() for line in text.splitlines() if line.strip()]

    @staticmethod
    def _up(value: str) -> str:
        """Remove accents and uppercase for comparison."""
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(c for c in normalized if not unicodedata.combining(c)).upper()

    @staticmethod
    def _is_label_line(line_upper: str) -> bool:
        """Check if a line looks like a known INE label."""
        for lbl in _STOP_LABELS:
            if line_upper.startswith(lbl) or re.search(rf"\b{lbl}\b", line_upper):
                return True
        return False

    # Words that should NEVER be accepted as a person's name
    _NOT_A_NAME = frozenset([
        "FECHA", "NACIMIENTO", "FECHA DE NACIMIENTO", "DOMICILIO",
        "CURP", "CLAVE", "ELECTOR", "SECCION", "VIGENCIA",
        "SEXO", "NACIONALIDAD", "REGISTRO", "EMISION",
        "ESTADO", "MUNICIPIO", "LOCALIDAD", "INSTITUTO",
        "NACIONAL", "ELECTORAL", "CREDENCIAL",
    ])

    @classmethod
    def _looks_like_name(cls, value: str) -> bool:
        """Check if a string looks like a name (only letters and spaces, not a known label)."""
        cleaned = re.sub(r"[^A-ZÁÉÍÓÚÑÜ\s]", "", value.upper()).strip()
        if len(cleaned) < 2 or re.search(r"\d{3,}", value):
            return False
        # Reject if the entire string matches a known INE label
        if cleaned in cls._NOT_A_NAME:
            return False
        # Reject if it starts with a known label word
        first_word = cleaned.split()[0] if cleaned.split() else ""
        if first_word in cls._NOT_A_NAME:
            return False
        return True

    # ── Name Block Extraction (Modern INE) ─────────────────────────────────

    def _extract_name_block(self, lines: list[str]) -> tuple[str | None, str | None, str | None]:
        """Extract the name block from modern INE format.

        Modern INE has:
            NOMBRE
            <APELLIDO PATERNO>     ← line after NOMBRE
            <APELLIDO MATERNO>     ← next line
            <NOMBRE(S)>            ← next line
            DOMICILIO / FECHA DE NACIMIENTO / other label

        Returns (nombre, apellido_paterno, apellido_materno).
        """
        nombre_idx = None
        for idx, line in enumerate(lines):
            line_upper = self._up(line)
            # Find the "NOMBRE" label line - but NOT "APELLIDO" or "INSTITUTO" lines
            if (re.search(r"\bNOMBRE\b", line_upper)
                    and not re.search(r"APELLIDO|COMPLETO|INSTITUTO|ELECTORAL|CREDENCIAL", line_upper)):
                nombre_idx = idx
                break

        if nombre_idx is None:
            return None, None, None

        # Check if there's a value on the same line as NOMBRE
        nombre_line = self._up(lines[nombre_idx])
        value_on_line = re.sub(r"\bNOMBRE\(?S?\)?\b", "", nombre_line).strip(" :")
        value_on_line = re.sub(r"^[:\-\s]+", "", value_on_line).strip()

        # Collect the name lines after the NOMBRE label
        name_lines: list[str] = []

        # If there's a value on the NOMBRE line itself, include it
        if value_on_line and len(value_on_line) > 1 and self._looks_like_name(value_on_line):
            name_lines.append(value_on_line)

        # Read subsequent lines until we hit a known label or non-name content
        for i in range(nombre_idx + 1, min(nombre_idx + 5, len(lines))):
            candidate = lines[i].strip()
            candidate_upper = self._up(candidate)

            # Stop if we hit a known label
            if self._is_label_line(candidate_upper):
                break

            # Stop if we see FECHA DE NACIMIENTO (it's on the right side of INE)
            if re.search(r"FECHA\s*DE\s*NACIMIENTO|F\.\s*NAC", candidate_upper):
                break

            # Stop if we see a date pattern (birth date next to name area)
            if re.search(r"\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}", candidate):
                break

            # Stop if we see SEXO
            if re.search(r"\bSEXO\b", candidate_upper):
                break

            # Stop if the line looks like a CURP or clave de elector
            if re.search(r"[A-Z]{4}\d{6}", candidate_upper):
                break

            # Accept the line if it looks like a name
            if self._looks_like_name(candidate):
                name_lines.append(self._clean_name(candidate) or candidate)
            else:
                break

            # Max 3 name lines (apellido paterno, materno, nombre)
            if len(name_lines) >= 3:
                break

        logger.info("INE name_lines extracted: %s", name_lines)

        if len(name_lines) == 0:
            return None, None, None
        elif len(name_lines) == 1:
            # Only one name line - could be just the apellido paterno or full name
            return name_lines[0], name_lines[0], None
        elif len(name_lines) == 2:
            # Two lines: apellido paterno + nombre (or apellido paterno + materno)
            return name_lines[1], name_lines[0], None
        else:
            # Three lines: apellido paterno, apellido materno, nombre(s)
            return name_lines[2], name_lines[0], name_lines[1]

    # ── Labeled Field Extraction (Older INE) ───────────────────────────────

    def _extract_labeled_field(
        self,
        lines: list[str],
        patterns: list[str],
        skip_if_contains: list[str] | None = None,
    ) -> str | None:
        """Extract a value after a label, either on the same line or the next."""
        for idx, line in enumerate(lines):
            line_upper = self._up(line)
            for pattern in patterns:
                if not re.search(pattern, line_upper):
                    continue

                # Skip if line contains any skip keywords
                if skip_if_contains:
                    if any(kw in line_upper for kw in skip_if_contains):
                        continue

                # Try value on same line
                cleaned = re.sub(pattern, "", line_upper).strip(" :")
                cleaned = re.sub(r"^[:\-\s]+", "", cleaned).strip()
                if cleaned and len(cleaned) > 1 and self._looks_like_name(cleaned):
                    return self._clean_name(cleaned)

                # Try next line
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip()
                    next_upper = self._up(next_line)
                    if not self._is_label_line(next_upper) and len(next_line) > 1:
                        return self._clean_name(next_line)
        return None

    # ── Address Extraction ─────────────────────────────────────────────────

    def _extract_domicilio(self, lines: list[str]) -> str | None:
        """Extract address (domicilio). May span multiple lines."""
        parts: list[str] = []
        collecting = False

        for line in lines:
            line_upper = self._up(line)

            if re.search(r"\bDOMICILIO\b", line_upper):
                collecting = True
                cleaned = re.sub(r"\bDOMICILIO\b", "", line_upper).strip(" :")
                cleaned = re.sub(r"^[:\-\s]+", "", cleaned).strip()
                if cleaned and len(cleaned) > 2:
                    parts.append(self._clean_value(cleaned) or cleaned)
                continue

            if collecting:
                if any(re.search(rf"\b{lbl}\b", line_upper) for lbl in _ADDRESS_STOP_LABELS):
                    break
                if re.search(r"[A-Z]{4}\d{6}", line_upper):
                    break
                if len(line.strip()) > 2:
                    parts.append(line.strip())
                if len(parts) >= 4:
                    break

        return ", ".join(parts) if parts else None

    # ── CURP Extraction ────────────────────────────────────────────────────

    def _extract_curp(self, text: str) -> str | None:
        """Extract CURP using regex pattern."""
        text_upper = self._up(text)
        # Standard CURP: 4 letters + 6 digits + H/M + 5 letters + alphanumeric + digit
        match = re.search(r"\b([A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d)\b", text_upper)
        if match:
            return match.group(1)

        # Fallback: look for CURP label
        lines = self._get_lines(text)
        for idx, line in enumerate(lines):
            if "CURP" in self._up(line):
                cleaned = re.sub(r"CURP\s*:?\s*", "", self._up(line))
                m = re.search(r"[A-Z]{4}\d{6}[A-Z0-9]{6,8}", cleaned)
                if m:
                    return m.group(0)
                if idx + 1 < len(lines):
                    m = re.search(r"[A-Z]{4}\d{6}[A-Z0-9]{6,8}", self._up(lines[idx + 1]))
                    if m:
                        return m.group(0)
        return None

    # ── Birth Date Extraction ──────────────────────────────────────────────

    def _extract_fecha_nacimiento(self, lines: list[str], text: str, curp: str | None) -> date | None:
        """Extract birth date from text or derive from CURP."""
        # Strategy 1: Look for labeled date
        for idx, line in enumerate(lines):
            line_upper = self._up(line)
            if re.search(r"FECHA\s*DE\s*NACIMIENTO|F\.?\s*NAC|NACIMIENTO", line_upper):
                dates = re.findall(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}\b", line)
                if dates:
                    parsed = parse_date_safe(dates[0])
                    if parsed:
                        return parsed
                if idx + 1 < len(lines):
                    dates = re.findall(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}\b", lines[idx + 1])
                    if dates:
                        parsed = parse_date_safe(dates[0])
                        if parsed:
                            return parsed

        # Strategy 2: Find first plausible birth date in text
        all_dates = re.findall(r"\b(\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4})\b", text)
        for d in all_dates:
            parsed = parse_date_safe(d)
            if parsed and parsed.year < 2010:
                return parsed

        # Strategy 3: Derive from CURP
        if curp and len(curp) >= 10:
            try:
                year = int(curp[4:6])
                month = int(curp[6:8])
                day = int(curp[8:10])
                century = 1900 if year > 30 else 2000
                return date(century + year, month, day)
            except (ValueError, IndexError):
                pass

        return None

    # ── Sex Extraction ─────────────────────────────────────────────────────

    def _extract_sexo(self, lines: list[str], text: str, curp: str | None) -> str | None:
        """Extract sex from text or CURP."""
        text_upper = self._up(text)

        match = re.search(r"SEXO\s*[:\s]\s*(M|F|H|MASCULINO|FEMENINO|HOMBRE|MUJER)", text_upper)
        if match:
            return self._normalize_sex(match.group(1))

        for idx, line in enumerate(lines):
            line_upper = self._up(line)
            if "SEXO" in line_upper:
                sex_match = re.search(r"\b(M|F|H)\b", re.sub(r"SEXO", "", line_upper))
                if sex_match:
                    return self._normalize_sex(sex_match.group(1))
                if idx + 1 < len(lines):
                    sex_match = re.search(r"\b(M|F|H)\b", self._up(lines[idx + 1]))
                    if sex_match:
                        return self._normalize_sex(sex_match.group(1))

        if curp and len(curp) >= 11:
            sex_char = curp[10]
            if sex_char in ("H", "M"):
                return self._normalize_sex(sex_char)

        return None

    # ── Nationality Extraction ─────────────────────────────────────────────

    def _extract_nacionalidad(self, text: str) -> str | None:
        """Extract nationality."""
        text_upper = self._up(text)
        if "MEXICANA" in text_upper:
            return "MEXICANA"
        match = re.search(r"NACIONALIDAD\s*[:\s]\s*(\w+)", text_upper)
        if match:
            return match.group(1)
        return "MEXICANA"

    # ── Clave de Elector Extraction ────────────────────────────────────────

    def _extract_clave_elector(self, text: str) -> str | None:
        """Extract clave de elector."""
        text_upper = self._up(text)
        # Labeled: "CLAVE DE ELECTOR ALMRFL67061130H800"
        match = re.search(r"CLAVE\s*(?:DE\s*)?ELECTOR\s*[:\s]*([A-Z0-9]{10,18})", text_upper)
        if match:
            return match.group(1)
        # Standalone 18-char alphanumeric that looks like clave
        match = re.search(r"\b([A-Z]{6}\d{8}[HM]\d{3})\b", text_upper)
        if match:
            return match.group(1)
        return None

    # ── Utility Methods ────────────────────────────────────────────────────

    @staticmethod
    def _normalize_sex(value: str) -> str:
        v = value.strip().upper()
        if v in ("H", "HOMBRE", "MASCULINO"):
            return "H"
        if v in ("M", "MUJER", "FEMENINO"):
            return "M"
        if v == "F":
            return "F"
        return v

    @staticmethod
    def _clean_name(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"[^A-ZÁÉÍÓÚÑÜ\s]", "", value.upper())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned if len(cleaned) > 1 else None

    @staticmethod
    def _clean_value(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip()
        return cleaned if cleaned else None

    @staticmethod
    def _build_full_name(ap_paterno: str | None, ap_materno: str | None, nombre: str | None) -> str | None:
        """Build full name in INE order: APELLIDO_PATERNO APELLIDO_MATERNO NOMBRE(S)."""
        parts = [p for p in [ap_paterno, ap_materno, nombre] if p]
        return " ".join(parts) if parts else None
