from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

output_path = Path("/tmp/facer_test_document.png")
image = Image.new("RGB", (1400, 900), "white")
draw = ImageDraw.Draw(image)
draw.rectangle((120, 120, 1280, 780), outline="black", width=6)
draw.text((180, 200), "INSTITUTO NACIONAL ELECTORAL", fill="black")
draw.text((180, 280), "NOMBRE", fill="black")
draw.text((180, 340), "JUAN CARLOS PEREZ LOPEZ", fill="black")
draw.text((180, 420), "CURP PERJ900101HDFLRN09", fill="black")
draw.text((180, 500), "1234567890123", fill="black")
draw.text((180, 580), "01/01/1990", fill="black")
image.save(output_path)
print(output_path)
