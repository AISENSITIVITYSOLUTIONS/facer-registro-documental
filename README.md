# FaceR Fase 2 - Backend de Validación Documental

Este repositorio contiene el backend en **Python FastAPI** para la **Fase 2 de validación documental de identidad** de FaceR. El servicio recibe imágenes de documentos oficiales, las almacena en un bucket privado, ejecuta OCR con Google Cloud Vision, estructura los datos básicos de identidad, compara el resultado contra el registro institucional de Fase 1 y persiste el resultado en MySQL.

La solución fue diseñada con una regla funcional central: **los datos capturados por OCR no se editan**. Si una captura sale deficiente o incompleta, el flujo permitido es la **recaptura o reintento de la imagen**, nunca la edición manual del contenido extraído. Esto reduce el riesgo de manipulación posterior al OCR y mantiene trazabilidad mediante auditoría.

| Componente | Implementación |
|---|---|
| Framework API | FastAPI |
| Validación de datos | Pydantic v2 |
| Persistencia | SQLAlchemy + MySQL / Cloud SQL |
| OCR | Google Cloud Vision API |
| Imágenes | Google Cloud Storage privado |
| Contenerización | Docker |
| Despliegue objetivo | Google Cloud Run |

## Alcance funcional

El backend cubre el ciclo documental mínimo requerido para identificar a la persona con los datos básicos definidos por negocio. Se soportan **INE México**, **pasaporte mexicano**, **cédula colombiana** y **pasaporte colombiano**, manteniendo únicamente los campos necesarios para validación de identidad y evitando sobrecargar el modelo con atributos no solicitados.

| Flujo | Descripción |
|---|---|
| Carga | Valida MIME type, tamaño, archivo no vacío y calidad básica de imagen |
| Almacenamiento | Guarda la imagen en GCS con nombre UUID y ruta privada |
| Procesamiento | Ejecuta OCR documental y heurísticas de extracción por tipo de documento |
| Comparación | Normaliza nombres y compara contra el registro institucional |
| Confirmación | Permite confirmar el resultado sin editar el contenido capturado |
| Reintento | Permite recaptura de imagen hasta el máximo configurado |
| Auditoría | Registra eventos relevantes del documento en `document_audit_log` |

## Estructura del proyecto

La estructura fue organizada para que el proyecto pueda abrirse directamente en **Visual Studio Code**, ejecutarse localmente y desplegarse en contenedor sin ajustes estructurales adicionales.

| Ruta | Propósito |
|---|---|
| `main.py` | Wrapper raíz para Cloud Run y ejecución directa |
| `config.py` | Wrapper raíz de configuración |
| `db.py` | Wrapper raíz de acceso a base de datos |
| `app/main.py` | Aplicación FastAPI y registro de rutas |
| `app/config.py` | Variables de entorno y configuración central |
| `app/db.py` | Engine, sesión y dependencia `get_db` |
| `app/models/` | Modelos ORM y enums |
| `app/repositories/` | Acceso a datos de usuarios y documentos |
| `app/services/` | OCR, almacenamiento, parsing, comparación y auditoría |
| `app/routers/` | Endpoints HTTP |
| `app/schemas/` | Schemas Pydantic de entrada y salida |
| `app/utils/` | Validaciones, normalización y utilidades |
| `sql/schema.sql` | Esquema SQL inicial |

## Modelo de datos

La persistencia sigue el principio de **campos básicos y suficientes**. No se incluyeron campos de edición manual del OCR ni atributos accesorios fuera del flujo principal.

| Tabla | Uso |
|---|---|
| `institutions` | Instituciones registradas |
| `users` | Referencia institucional de Fase 1 |
| `identity_documents` | Documento capturado, OCR, comparación y estados |
| `document_audit_log` | Trazabilidad de eventos del documento |

## Endpoints principales

La API publica su versión bajo el prefijo configurable `API_V1_PREFIX`.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Health check del servicio |
| `GET` | `/api/v1/users/{user_id}` | Consulta el usuario institucional |
| `GET` | `/api/v1/users/{user_id}/document-status` | Resume el estado documental más reciente |
| `POST` | `/api/v1/documents/upload` | Carga imagen documental |
| `POST` | `/api/v1/documents/{document_id}/process` | Ejecuta OCR, parsing y comparación |
| `GET` | `/api/v1/documents/{document_id}/results` | Devuelve resultado estructurado |
| `POST` | `/api/v1/documents/{document_id}/confirm` | Confirma el documento sin edición |
| `POST` | `/api/v1/documents/{document_id}/retry` | Reemplaza la imagen por recaptura |

## Variables de entorno

La configuración se centraliza en `app/config.py` y se ejemplifica en `.env.example`.

| Variable | Descripción |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Conexión MySQL local o administrada |
| `CLOUD_SQL_CONNECTION_NAME` | Habilita conexión por Unix socket para Cloud SQL |
| `DATABASE_URL` | Sobrescribe la cadena completa de conexión si se desea |
| `GCP_PROJECT_ID` | Proyecto de Google Cloud |
| `GCS_BUCKET_NAME` | Bucket privado para imágenes documentales |
| `GCS_DOCUMENTS_PREFIX` | Prefijo interno del bucket |
| `MAX_UPLOAD_SIZE_BYTES` | Tamaño máximo del archivo |
| `MIN_IMAGE_WIDTH`, `MIN_IMAGE_HEIGHT` | Reglas mínimas de imagen |
| `MIN_CAPTURE_QUALITY_SCORE` | Umbral de calidad para advertir recaptura |
| `MAX_RETRY_COUNT` | Reintentos máximos permitidos |

## Ejecución local

Para desarrollo local, cree un entorno virtual, instale dependencias, copie `.env.example` a `.env` y complete las variables necesarias. Si va a probar OCR y almacenamiento real, deberá contar con credenciales de Google Cloud disponibles en el entorno.

| Paso | Comando |
|---|---|
| Instalar dependencias | `pip install -r requirements.txt` |
| Configurar variables | `cp .env.example .env` |
| Ejecutar API | `uvicorn main:app --reload --host 0.0.0.0 --port 8080` |

## Despliegue en Cloud Run

El contenedor ya queda preparado para ejecución en Cloud Run. La aplicación escucha por la variable `PORT`, utiliza configuración por variables de entorno y puede conectarse a Cloud SQL mediante `CLOUD_SQL_CONNECTION_NAME` o por una URL completa de base de datos.

| Recurso | Consideración |
|---|---|
| Cloud Run | Desplegar la imagen usando el `Dockerfile` incluido |
| Cloud SQL MySQL | Configurar variables y, si aplica, instancia vinculada |
| GCS | Mantener bucket privado y permisos del service account |
| Vision API | Habilitar la API y permisos de invocación |

## Reglas de seguridad implementadas

La solución incorpora validaciones orientadas a operación segura y consistente. Se rechazan archivos vacíos, tipos MIME no permitidos y cargas que excedan el límite configurado. Los nombres de archivo almacenados en GCS utilizan **UUID**. Los eventos de negocio se registran en auditoría sin persistir información sensible adicional fuera del modelo documental requerido.

| Regla | Aplicación |
|---|---|
| Sin edición OCR | Solo existe confirmación o recaptura |
| Bucket privado | Ruta `gs://` almacenada sin exposición pública |
| Validación de archivo | MIME, tamaño y contenido no vacío |
| Manejo de errores | Respuestas HTTP controladas y rollback en DB |
| Logs funcionales | Auditoría de acciones, no de PII extra innecesaria |

## Notas de implementación

El motor de comparación normaliza mayúsculas, acentos y espacios antes de calcular la similitud. El estado final del documento combina la calidad de captura, el parsing heurístico y la coincidencia con el registro institucional. Dado que la tabla `users` de Fase 1 se mantuvo con el alcance mínimo solicitado, la comparación de fecha de nacimiento queda preparada para ampliarse si la institución incorpora ese dato en su fuente maestra futura.
