from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
os.environ.setdefault("AUTH_API_KEY", "local-dev-change-me")

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Institution, User


def build_sample_image() -> bytes:
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

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def ensure_sample_user() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        institution = db.query(Institution).filter(Institution.code == "LOCAL-DEMO").one_or_none()
        if institution is None:
            institution = Institution(name="Local Demo", code="LOCAL-DEMO")
            db.add(institution)
            db.flush()

        user = db.query(User).filter(User.institutional_id == "LOCAL-USER-001").one_or_none()
        if user is None:
            user = User(
                first_name="JUAN",
                last_name="PEREZ LOPEZ",
                institutional_id="LOCAL-USER-001",
                institution_id=institution.id,
            )
            db.add(user)
            db.flush()

        db.commit()
        return int(user.id)
    finally:
        db.close()


def main() -> None:
    user_id = ensure_sample_user()
    image_bytes = build_sample_image()

    client = TestClient(app)
    headers = {
        "X-API-Key": settings.auth_api_key,
        "X-Institution-Code": "LOCAL-DEMO",
    }

    upload_response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={
            "user_id": str(user_id),
            "country": "MX",
            "document_type": "INE",
        },
        files={
            "file": ("ine-demo.png", image_bytes, "image/png"),
        },
    )
    upload_response.raise_for_status()
    upload_payload = upload_response.json()

    process_response = client.post(
        f"/api/v1/documents/{upload_payload['id']}/process",
        headers=headers,
    )
    process_response.raise_for_status()
    process_payload = process_response.json()

    print("Upload response:")
    print(upload_payload)
    print()
    print("Process response:")
    print(process_payload)


if __name__ == "__main__":
    main()
