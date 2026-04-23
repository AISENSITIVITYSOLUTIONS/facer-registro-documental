from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.models import DocumentType
from app.services import ParsingService


def main() -> None:
    raw_text = """
    MEXICO
    INSTITUTO NACIONAL ELECTORAL
    CREDENCIAL PARA VOTAR
    NOMBRE
    MORALES
    DE ALBA
    WNIK IVANOVICH
    SEXO H
    DOMICILIO
    C RUBI 4
    FRACC BUGAMBILIAS 91637
    EMILIANO ZAPATA, VER.
    CLAVE DE ELECTOR MRALWN95123030H400
    CURP MOAVW951230HVZRLN00
    FECHA DE NACIMIENTO
    30/12/1995
    SECCION 1480
    VIGENCIA
    2022 - 2032
    """

    ocr_lines = [
        {"text": "NOMBRE", "box": [[520, 240], [650, 240], [650, 290], [520, 290]]},
        {"text": "$EX0 H", "box": [[990, 248], [1071, 248], [1071, 290], [990, 290]]},
        {"text": "E", "box": [[1185, 252], [1198, 252], [1198, 286], [1185, 286]]},
        {"text": "E1", "box": [[1202, 252], [1214, 252], [1214, 286], [1202, 286]]},
        {"text": "MORALES", "box": [[515, 285], [700, 285], [700, 335], [515, 335]]},
        {"text": "DE ALBA", "box": [[515, 335], [700, 335], [700, 385], [515, 385]]},
        {"text": "WNIK IVANOVICH", "box": [[515, 385], [860, 385], [860, 440], [515, 440]]},
        {"text": "SEXO H", "box": [[1320, 230], [1470, 230], [1470, 285], [1320, 285]]},
        {"text": "DOMICILIO", "box": [[520, 510], [730, 510], [730, 555], [520, 555]]},
        {"text": "C RUBI 4", "box": [[520, 555], [700, 555], [700, 605], [520, 605]]},
        {"text": "FRACC BUGAMBILIAS 91637", "box": [[520, 605], [980, 605], [980, 655], [520, 655]]},
        {"text": "EMILIANO ZAPATA, VER.", "box": [[520, 655], [930, 655], [930, 705], [520, 705]]},
    ]

    parsing_service = ParsingService()
    result = parsing_service.parse_document(
        document_type=DocumentType.INE,
        raw_text=raw_text,
        ocr_lines=ocr_lines,
    )

    fields = result["fields"]
    print("Parsed fields:")
    print(fields)
    assert fields["full_name"] == "MORALES DE ALBA WNIK IVANOVICH"
    assert fields["first_name"] == "MORALES"
    assert fields["last_name"] == "DE ALBA"
    assert fields["address"] == "C RUBI 4 FRACC BUGAMBILIAS 91637 EMILIANO ZAPATA, VER"
    assert str(fields["birth_date"]) == "1995-12-30"
    assert fields["sex"] == "H"
    assert fields["document_number"] == "MRALWN95123030H400"
    assert fields["curp"] is not None
    assert str(fields["expiration_date"]) == "2032-12-31"
    print("INE parser validation passed.")

    second_raw_text = """
    MEXICO
    INSTITUTO NACIONAL ELECTORAL
    CREDENCIAL PARA VOTAR
    NOMBRE
    DE ALBA
    MURRIETA
    FELIPE DE JESUS
    DOMICILIO
    C HUATUSCO 13 5
    COL ROMA SUR 06760
    CUAUHTEMOC, CDMX
    CURP AAMF670611HVZLRL07
    FECHA DE NACIMIENTO 11/06/1967
    VIGENCIA 2027
    """
    second_ocr_lines = [
        {"text": "NOMBRE", "box": [[350, 250], [470, 250], [470, 295], [350, 295]]},
        {"text": "DE ALBA", "box": [[350, 295], [520, 295], [520, 340], [350, 340]]},
        {"text": "MURRIETA", "box": [[350, 340], [580, 340], [580, 385], [350, 385]]},
        {"text": "FELIPE DE JESUS", "box": [[350, 385], [690, 385], [690, 430], [350, 430]]},
        {"text": "DOMICILIO", "box": [[350, 455], [540, 455], [540, 500], [350, 500]]},
        {"text": "C HUATUSCO 13 5", "box": [[350, 500], [650, 500], [650, 545], [350, 545]]},
        {"text": "COL ROMA SUR 06760", "box": [[350, 545], [710, 545], [710, 590], [350, 590]]},
        {"text": "CUAUHTEMOC, CDMX", "box": [[350, 590], [690, 590], [690, 635], [350, 635]]},
    ]

    second_result = parsing_service.parse_document(
        document_type=DocumentType.INE,
        raw_text=second_raw_text,
        ocr_lines=second_ocr_lines,
    )

    second_fields = second_result["fields"]
    print("Second parsed fields:")
    print(second_fields)
    assert second_fields["full_name"] == "DE ALBA MURRIETA FELIPE DE JESUS"
    assert second_fields["first_name"] == "DE ALBA"
    assert second_fields["last_name"] == "MURRIETA"
    assert second_fields["address"] == "C HUATUSCO 13 5 COL ROMA SUR 06760 CUAUHTEMOC, CDMX"
    assert second_fields["curp"] == "AAMF670611HVZLRL07"
    assert str(second_fields["birth_date"]) == "1967-06-11"
    assert str(second_fields["expiration_date"]) == "2027-12-31"
    print("Second INE parser validation passed.")


if __name__ == "__main__":
    main()
