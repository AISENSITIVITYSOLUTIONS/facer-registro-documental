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

Uses pattern matching specific to INE layout which has labeled fields:
NOMBRE, APELLIDO PATERNO, APELLIDO MATERNO, DOMICILIO, CURP, etc.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

from app.utils.validators import is_valid_curp, parse_date_safe


class INEParsingService:
    """Parse OCR text from Mexican INE documents with high accuracy."""

    def parse(self, raw_text: str) -> dict[str, Any]:
        """Parse raw OCR text and extract INE fields."""
        normalized = self._prepare_text(raw_text)
        lines = self._get_lines(normalized)

        # Extract fields using multiple strategies
        apellido_paterno = self._extract_apellido_paterno(lines, normalized)
        apellido_materno = self._extract_apellido_materno(lines, normalized)
        nombre = self._extract_nombre(lines, normalized)
        domicilio = self._extract_domicilio(lines, normalized)
        curp = self._extract_curp(normalized)
        fecha_nacimiento = self._extract_fecha_nacimiento(lines, normalized, curp)
        sexo = self._extract_sexo(lines, normalized, curp)
        nacionalidad = self._extract_nacionalidad(lines, normalized)
        clave_elector = self._extract_clave_elector(normalized)
        seccion = self._extract_seccion(normalized)

        # Build full name
        nombre_completo = self._build_full_name(nombre, apellido_paterno, apellido_materno)

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
            "seccion": seccion,
            # Compatibility fields for existing system
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
        """Get non-empty lines."""
        return [line.strip() for line in text.splitlines() if line.strip()]

    @staticmethod
    def _accentless_upper(value: str) -> str:
        """Remove accents and uppercase."""
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(char for char in normalized if not unicodedata.combining(char)).upper()

    def _extract_labeled_value(self, lines: list[str], labels: list[str], skip_labels: list[str] | None = None) -> str | None:
        """Extract value after a label, either on same line or next line."""
        for idx, line in enumerate(lines):
            line_upper = self._accentless_upper(line)
            for label in labels:
                pattern = re.compile(label, re.IGNORECASE)
                if pattern.search(line_upper):
                    # Check if there's a value on the same line after the label
                    cleaned = pattern.sub("", line_upper).strip(" :")
                    # Remove common noise
                    cleaned = re.sub(r"^[:\-\s]+", "", cleaned).strip()
                    if cleaned and len(cleaned) > 1:
                        # Check it's not another label
                        if skip_labels:
                            is_label = any(re.search(sl, cleaned, re.IGNORECASE) for sl in skip_labels)
                            if is_label:
                                continue
                        return self._clean_value(cleaned)
                    # Value is on the next line
                    if idx + 1 < len(lines):
                        next_line = lines[idx + 1].strip()
                        next_upper = self._accentless_upper(next_line)
                        # Make sure next line isn't another label
                        common_labels = ["NOMBRE", "APELLIDO", "DOMICILIO", "CURP", "FECHA", "SEXO",
                                         "NACIONALIDAD", "CLAVE", "SECCION", "VIGENCIA", "ESTADO"]
                        is_next_label = any(next_upper.startswith(lbl) for lbl in common_labels)
                        if not is_next_label and len(next_line) > 1:
                            return self._clean_value(next_line)
            return None
        return None

    def _extract_apellido_paterno(self, lines: list[str], text: str) -> str | None:
        """Extract paternal surname."""
        # Strategy 1: Look for explicit label
        patterns = [
            r"APELLIDO\s*PATERNO",
            r"AP(?:ELLIDO)?\s*PAT(?:ERNO)?",
            r"PATERNO",
        ]
        for idx, line in enumerate(lines):
            line_upper = self._accentless_upper(line)
            for pattern in patterns:
                if re.search(pattern, line_upper):
                    # Value after label on same line
                    cleaned = re.sub(pattern, "", line_upper).strip(" :")
                    cleaned = re.sub(r"^[:\-\s]+", "", cleaned).strip()
                    if cleaned and len(cleaned) > 1 and not re.search(r"MATERNO|NOMBRE", cleaned):
                        return self._clean_name(cleaned)
                    # Next line
                    if idx + 1 < len(lines):
                        next_line = lines[idx + 1].strip()
                        next_upper = self._accentless_upper(next_line)
                        if not re.search(r"APELLIDO|MATERNO|NOMBRE|DOMICILIO|CURP", next_upper) and len(next_line) > 1:
                            return self._clean_name(next_line)
        return None

    def _extract_apellido_materno(self, lines: list[str], text: str) -> str | None:
        """Extract maternal surname."""
        patterns = [
            r"APELLIDO\s*MATERNO",
            r"AP(?:ELLIDO)?\s*MAT(?:ERNO)?",
            r"MATERNO",
        ]
        for idx, line in enumerate(lines):
            line_upper = self._accentless_upper(line)
            for pattern in patterns:
                if re.search(pattern, line_upper):
                    cleaned = re.sub(pattern, "", line_upper).strip(" :")
                    cleaned = re.sub(r"^[:\-\s]+", "", cleaned).strip()
                    if cleaned and len(cleaned) > 1 and not re.search(r"PATERNO|NOMBRE|DOMICILIO", cleaned):
                        return self._clean_name(cleaned)
                    if idx + 1 < len(lines):
                        next_line = lines[idx + 1].strip()
                        next_upper = self._accentless_upper(next_line)
                        if not re.search(r"APELLIDO|PATERNO|NOMBRE|DOMICILIO|CURP", next_upper) and len(next_line) > 1:
                            return self._clean_name(next_line)
        return None

    def _extract_nombre(self, lines: list[str], text: str) -> str | None:
        """Extract first name(s)."""
        # Look for NOMBRE label that is NOT APELLIDO
        for idx, line in enumerate(lines):
            line_upper = self._accentless_upper(line)
            # Match "NOMBRE" but not "APELLIDO" context
            if re.search(r"\bNOMBRE\b", line_upper) and not re.search(r"APELLIDO|COMPLETO", line_upper):
                cleaned = re.sub(r"\bNOMBRE\(?S?\)?\b", "", line_upper).strip(" :")
                cleaned = re.sub(r"^[:\-\s]+", "", cleaned).strip()
                if cleaned and len(cleaned) > 1 and not re.search(r"APELLIDO|DOMICILIO|CURP|PATERNO|MATERNO", cleaned):
                    return self._clean_name(cleaned)
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip()
                    next_upper = self._accentless_upper(next_line)
                    if not re.search(r"APELLIDO|DOMICILIO|CURP|SEXO|FECHA", next_upper) and len(next_line) > 1:
                        return self._clean_name(next_line)
        return None

    def _extract_domicilio(self, lines: list[str], text: str) -> str | None:
        """Extract address (domicilio). May span multiple lines."""
        domicilio_parts: list[str] = []
        collecting = False
        stop_labels = ["CURP", "CLAVE", "SECCION", "VIGENCIA", "FECHA", "ESTADO",
                       "MUNICIPIO", "AÑO DE REGISTRO", "EMISION"]

        for idx, line in enumerate(lines):
            line_upper = self._accentless_upper(line)

            if re.search(r"\bDOMICILIO\b", line_upper):
                collecting = True
                # Check if value is on same line
                cleaned = re.sub(r"\bDOMICILIO\b", "", line_upper).strip(" :")
                cleaned = re.sub(r"^[:\-\s]+", "", cleaned).strip()
                if cleaned and len(cleaned) > 2:
                    domicilio_parts.append(self._clean_value(cleaned))
                continue

            if collecting:
                # Stop if we hit another known label
                if any(re.search(rf"\b{lbl}\b", line_upper) for lbl in stop_labels):
                    break
                # Stop if we see CURP pattern
                if re.search(r"[A-Z]{4}\d{6}", line_upper):
                    break
                # Add line to address
                if len(line.strip()) > 2:
                    domicilio_parts.append(line.strip())
                # Limit to 4 lines max for address
                if len(domicilio_parts) >= 4:
                    break

        if domicilio_parts:
            return ", ".join(domicilio_parts)
        return None

    def _extract_curp(self, text: str) -> str | None:
        """Extract CURP using regex pattern."""
        # CURP format: 4 letters + 6 digits + H/M + 5 letters + alphanumeric + digit
        pattern = r"\b([A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d)\b"
        match = re.search(pattern, self._accentless_upper(text))
        if match:
            curp = match.group(1)
            if is_valid_curp(curp):
                return curp
            return curp  # Return even if not perfectly valid - Vision might have small errors
        
        # Fallback: look for CURP label and extract next alphanumeric sequence
        lines = self._get_lines(text)
        for idx, line in enumerate(lines):
            if "CURP" in self._accentless_upper(line):
                # Check same line
                cleaned = re.sub(r"CURP\s*:?\s*", "", self._accentless_upper(line))
                curp_match = re.search(r"[A-Z]{4}\d{6}[A-Z0-9]{6,8}", cleaned)
                if curp_match:
                    return curp_match.group(0)
                # Check next line
                if idx + 1 < len(lines):
                    next_upper = self._accentless_upper(lines[idx + 1])
                    curp_match = re.search(r"[A-Z]{4}\d{6}[A-Z0-9]{6,8}", next_upper)
                    if curp_match:
                        return curp_match.group(0)
        return None

    def _extract_fecha_nacimiento(self, lines: list[str], text: str, curp: str | None) -> date | None:
        """Extract birth date from text or derive from CURP."""
        # Strategy 1: Look for labeled date
        for idx, line in enumerate(lines):
            line_upper = self._accentless_upper(line)
            if re.search(r"FECHA\s*DE\s*NACIMIENTO|F\.?\s*NAC|NACIMIENTO", line_upper):
                # Look for date on same line
                dates = re.findall(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}\b", line)
                if dates:
                    parsed = parse_date_safe(dates[0])
                    if parsed:
                        return parsed
                # Check next line
                if idx + 1 < len(lines):
                    dates = re.findall(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}\b", lines[idx + 1])
                    if dates:
                        parsed = parse_date_safe(dates[0])
                        if parsed:
                            return parsed

        # Strategy 2: Find first date in text (usually birth date on INE)
        all_dates = re.findall(r"\b(\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4})\b", text)
        for d in all_dates:
            parsed = parse_date_safe(d)
            if parsed and parsed.year < 2010:  # Birth dates should be before 2010
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

    def _extract_sexo(self, lines: list[str], text: str, curp: str | None) -> str | None:
        """Extract sex from text or CURP."""
        text_upper = self._accentless_upper(text)

        # Strategy 1: Look for labeled sex
        match = re.search(r"SEXO\s*[:\s]\s*(M|F|H|MASCULINO|FEMENINO|HOMBRE|MUJER)", text_upper)
        if match:
            return self._normalize_sex(match.group(1))

        # Strategy 2: Look for standalone M/F/H near SEXO context
        for idx, line in enumerate(lines):
            line_upper = self._accentless_upper(line)
            if "SEXO" in line_upper:
                sex_match = re.search(r"\b(M|F|H)\b", re.sub(r"SEXO", "", line_upper))
                if sex_match:
                    return self._normalize_sex(sex_match.group(1))
                if idx + 1 < len(lines):
                    sex_match = re.search(r"\b(M|F|H)\b", self._accentless_upper(lines[idx + 1]))
                    if sex_match:
                        return self._normalize_sex(sex_match.group(1))

        # Strategy 3: Derive from CURP (position 10 is H or M)
        if curp and len(curp) >= 11:
            sex_char = curp[10]
            if sex_char in ("H", "M"):
                return self._normalize_sex(sex_char)

        return None

    def _extract_nacionalidad(self, lines: list[str], text: str) -> str | None:
        """Extract nationality."""
        text_upper = self._accentless_upper(text)
        if "MEXICANA" in text_upper:
            return "MEXICANA"
        match = re.search(r"NACIONALIDAD\s*[:\s]\s*(\w+)", text_upper)
        if match:
            return match.group(1)
        return "MEXICANA"  # Default for INE

    def _extract_clave_elector(self, text: str) -> str | None:
        """Extract clave de elector (13 digits)."""
        text_upper = self._accentless_upper(text)
        # Look for labeled value
        match = re.search(r"CLAVE\s*(?:DE\s*)?ELECTOR\s*[:\s]\s*(\d{13,18})", text_upper)
        if match:
            return match.group(1)
        # Look for 13-digit number
        match = re.search(r"\b(\d{13})\b", text)
        if match:
            return match.group(1)
        return None

    def _extract_seccion(self, text: str) -> str | None:
        """Extract electoral section."""
        text_upper = self._accentless_upper(text)
        match = re.search(r"SECCION\s*[:\s]\s*(\d{3,4})", text_upper)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _normalize_sex(value: str) -> str:
        """Normalize sex value to M/F."""
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
        """Clean a name value."""
        if not value:
            return None
        # Remove non-letter characters except spaces
        cleaned = re.sub(r"[^A-ZÁÉÍÓÚÑÜ\s]", "", value.upper())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned if len(cleaned) > 1 else None

    @staticmethod
    def _clean_value(value: str | None) -> str | None:
        """Clean a generic value."""
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip()
        return cleaned if cleaned else None

    @staticmethod
    def _build_full_name(nombre: str | None, ap_paterno: str | None, ap_materno: str | None) -> str | None:
        """Build full name from parts."""
        parts = [p for p in [nombre, ap_paterno, ap_materno] if p]
        return " ".join(parts) if parts else None
