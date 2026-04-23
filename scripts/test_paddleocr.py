from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_IMAGE = ROOT_DIR / "tmp" / "ocr_test_document.png"
sys.path.insert(0, str(ROOT_DIR))

from app.models import DocumentType
from app.services import OCRService, ParsingService


def load_image_from_argument(raw_path: str) -> tuple[bytes, Path]:
    image_path = Path(raw_path).expanduser()
    if not image_path.is_absolute():
        image_path = (ROOT_DIR / image_path).resolve()
    else:
        image_path = image_path.resolve()

    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"No se encontro la imagen: {image_path}")

    return image_path.read_bytes(), image_path


def build_sample_image() -> bytes:
    OUTPUT_IMAGE.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (1800, 1100), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 46)

    lines = [
        "CREDENCIAL PARA VOTAR",
        "",
        "NOMBRE",
        "JUAN PEREZ LOPEZ",
        "SEXO H",
        "FECHA DE NACIMIENTO 01/01/1990",
        "CURP PELJ900101HDFRPN09",
        "CLAVE DE ELECTOR 1234567890123",
        "VIGENCIA 01/01/2030",
    ]

    y = 80
    for line in lines:
        draw.text((100, y), line, fill="black", font=font)
        y += 85

    image.save(OUTPUT_IMAGE)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    image_source = OUTPUT_IMAGE
    if len(sys.argv) > 1:
        image_bytes, image_source = load_image_from_argument(sys.argv[1])
    else:
        image_bytes = build_sample_image()

    ocr_service = OCRService()
    parsing_service = ParsingService()

    ocr_result = ocr_service.extract_text(image_bytes)
    parsing_result = parsing_service.parse_document(
        document_type=DocumentType.INE,
        raw_text=ocr_result["text"],
        ocr_lines=ocr_result.get("lines"),
        ocr_hints=ocr_result.get("field_hints"),
    )

    print("OCR engine:", ocr_result["engine"])
    print("OCR confidence:", ocr_result["confidence"])
    print("Preprocessing:", ocr_result.get("preprocessing"))
    print("OCR text:")
    print(ocr_result["text"])
    print()
    print("Parsed fields:")
    print(parsing_result["fields"])
    print("Validation status:", parsing_result["validation_status"])
    print("Image source:", image_source)


if __name__ == "__main__":
    main()
