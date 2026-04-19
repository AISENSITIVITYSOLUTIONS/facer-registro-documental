# FaceR Fase 2 - Backend de Validación Documental

Este repositorio contiene el backend en **Python FastAPI** para la validación documental de identidad. El servicio recibe imágenes de documentos oficiales, evalúa su calidad, las almacena, ejecuta OCR, estructura los datos básicos de identidad, compara el resultado contra el registro institucional y persiste el resultado para auditoría y validación.

En esta versión, el proyecto fue mejorado para funcionar mejor en **desarrollo local** y para servir como base de una futura **app móvil** o **web app** de captura documental. La arquitectura ya no depende exclusivamente de Google Cloud para operar en un entorno profesional de pruebas locales.

| Componente | Implementación actual |
|---|---|
| Framework API | FastAPI |
| Validación de datos | Pydantic v2 |
| Persistencia | SQLAlchemy con MySQL o SQLite |
| OCR | Tesseract local o Google Cloud Vision |
| Preprocesamiento | Pillow con variantes para mejorar OCR |
| Almacenamiento | Local filesystem o Google Cloud Storage |
| Contenerización | Docker |
| Objetivo de evolución | Backend reusable para app móvil y web app |

## Cambios principales introducidos

La versión actual incorpora una línea de mejora orientada a calidad de captura, operación local y desacoplamiento técnico.

| Mejora | Resultado |
|---|---|
| OCR configurable | Se puede usar `tesseract` en local o `google_vision` |
| Almacenamiento configurable | Se puede usar `local` o `gcs` |
| Base de datos portable | Se puede usar `DATABASE_URL` con SQLite para desarrollo local |
| Endpoint previo de captura | Se añadió `POST /api/v1/documents/analyze-capture` para evaluar calidad antes de cargar el documento |
| Preprocesamiento de imagen | Se generan variantes de imagen para aumentar legibilidad OCR |
| Parsing reforzado | Mejoras heurísticas para INE, pasaportes y cédula colombiana |
| Corrección funcional | Se corrigió la lógica de confirmación documental |

## Alcance funcional

El backend cubre el ciclo documental mínimo requerido para identificar a la persona con los datos básicos definidos por negocio. Se soportan **INE México**, **pasaporte mexicano**, **cédula colombiana** y **pasaporte colombiano**, manteniendo únicamente los campos necesarios para validación de identidad.

| Flujo | Descripción |
|---|---|
| Análisis de captura | Evalúa resolución, brillo, contraste, nitidez y reflejos antes de persistir la imagen |
| Carga | Valida MIME type, tamaño, archivo no vacío y calidad básica |
| Almacenamiento | Guarda la imagen en almacenamiento local o GCS |
| Procesamiento | Ejecuta OCR documental y heurísticas de extracción por tipo de documento |
| Comparación | Normaliza nombres y compara contra el registro institucional |
| Confirmación | Permite confirmar el documento sin editar el contenido extraído |
| Reintento | Permite recaptura de imagen hasta el máximo configurado |
| Auditoría | Registra eventos relevantes del documento en `document_audit_log` |

## Endpoints principales

La API publica su versión bajo el prefijo configurable `API_V1_PREFIX`.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Health check del servicio |
| `GET` | `/api/v1/users/{user_id}` | Consulta el usuario institucional |
| `GET` | `/api/v1/users/{user_id}/document-status` | Resume el estado documental más reciente |
| `POST` | `/api/v1/documents/analyze-capture` | Evalúa la calidad de una imagen antes de cargarla |
| `POST` | `/api/v1/documents/upload` | Carga imagen documental |
| `POST` | `/api/v1/documents/{document_id}/process` | Ejecuta OCR, parsing y comparación |
| `GET` | `/api/v1/documents/{document_id}/results` | Devuelve resultado estructurado |
| `POST` | `/api/v1/documents/{document_id}/confirm` | Confirma el documento sin edición |
| `POST` | `/api/v1/documents/{document_id}/retry` | Reemplaza la imagen por recaptura |

## Estructura del proyecto

| Ruta | Propósito |
|---|---|
| `main.py` | Wrapper raíz para Cloud Run y ejecución directa |
| `app/main.py` | Aplicación FastAPI y registro de rutas |
| `app/config.py` | Variables de entorno y configuración central |
| `app/db.py` | Engine, sesión y dependencia `get_db` |
| `app/models/` | Modelos ORM y enums |
| `app/repositories/` | Acceso a datos de usuarios y documentos |
| `app/services/ocr_service.py` | OCR configurable por motor |
| `app/services/storage_service.py` | Almacenamiento configurable por backend |
| `app/services/image_preprocessing_service.py` | Variantes de imagen para OCR |
| `app/services/parsing_service.py` | Parsing heurístico por tipo documental |
| `app/routers/` | Endpoints HTTP |
| `app/schemas/` | Schemas Pydantic de entrada y salida |
| `app/utils/` | Validaciones, normalización y utilidades |
| `sql/schema.sql` | Esquema SQL inicial |
| `analysis/` | Documentos internos de análisis y plan técnico |

## Variables de entorno

La configuración se centraliza en `app/config.py` y se ejemplifica en `.env.example`.

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Permite usar SQLite local o cualquier URI compatible con SQLAlchemy |
| `STORAGE_BACKEND` | `local` o `gcs` |
| `STORAGE_LOCAL_DIR` | Carpeta base para almacenamiento local |
| `DEFAULT_OCR_ENGINE` | `tesseract` o `google_vision` |
| `TESSERACT_LANGUAGES` | Idiomas del OCR local, por ejemplo `spa+eng` |
| `ENABLE_IMAGE_PREPROCESSING` | Activa variantes de preprocesamiento antes del OCR |
| `GCP_PROJECT_ID`, `GCS_BUCKET_NAME` | Requeridos si se usa GCS |
| `MAX_UPLOAD_SIZE_BYTES` | Tamaño máximo del archivo |
| `MIN_IMAGE_WIDTH`, `MIN_IMAGE_HEIGHT` | Reglas mínimas de imagen |
| `MIN_CAPTURE_QUALITY_SCORE` | Umbral de calidad para advertir recaptura |
| `MAX_RETRY_COUNT` | Reintentos máximos permitidos |

## Ejecución local recomendada

Para desarrollo local, se recomienda operar con **SQLite + almacenamiento local + Tesseract**. Ese modo reduce dependencias externas y permite validar el flujo completo de captura, OCR y persistencia antes de pasar a nube.

| Paso | Comando |
|---|---|
| Instalar dependencias Python | `pip install -r requirements.txt` |
| Instalar Tesseract en Ubuntu | `sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng` |
| Configurar variables | `cp .env.example .env` |
| Definir SQLite local | `DATABASE_URL=sqlite:///./data/facer_document_validation.db` |
| Ejecutar API | `uvicorn main:app --reload --host 0.0.0.0 --port 8080` |

## Estrategia recomendada para cliente móvil o web

Este repositorio sigue siendo un backend. No incluye todavía una app móvil ni una web app de captura. Sin embargo, ahora está mejor preparado para integrarse con un cliente de captura guiada.

| Cliente futuro | Recomendación |
|---|---|
| App móvil | Capturar imagen con flujo guiado, auto-recorte o scanner del sistema y enviar primero a `analyze-capture` |
| Web app | Usar cámara del navegador, capturar still, evaluar calidad y luego cargar a `upload` |
| Backend | Mantener toda la lógica de OCR, parsing, validación, auditoría y persistencia en este servicio |

## Reglas de seguridad implementadas

La solución rechaza archivos vacíos, tipos MIME no permitidos y cargas que excedan el límite configurado. Se mantiene la regla funcional de **no editar manualmente el resultado OCR**. El flujo permitido sigue siendo confirmar o recapturar, no alterar el contenido extraído.

| Regla | Aplicación |
|---|---|
| Sin edición OCR | Solo existe confirmación o recaptura |
| Validación de archivo | MIME, tamaño y contenido no vacío |
| Validación de calidad | Score de captura previo y posterior a la carga |
| Manejo de errores | Respuestas HTTP controladas y rollback en DB |
| Logs funcionales | Auditoría de acciones relevantes |

## Notas finales

El motor de comparación normaliza mayúsculas, acentos y espacios antes de calcular similitud. La calidad final del proceso depende tanto del OCR como de la captura de imagen. Por ello, para una fase posterior se recomienda implementar un cliente móvil o web con guía visual de encuadre, selección automática de cámara trasera y recaptura asistida antes de invocar el procesamiento definitivo.
