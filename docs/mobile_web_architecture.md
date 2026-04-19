# Arquitectura recomendada para evolución a app móvil o web app

## Propósito

Este documento describe cómo debería evolucionar el backend `facer-registro-documental` hacia una solución profesional con cliente móvil o web para captura documental de INE, pasaporte mexicano, cédula colombiana y pasaporte colombiano.

## Principio arquitectónico

El backend debe conservar la responsabilidad de **OCR, parsing, comparación, auditoría y persistencia**, mientras que el cliente debe asumir la responsabilidad de **captura guiada, selección de cámara, previsualización, encuadre y recaptura asistida**.

| Capa | Responsabilidad |
|---|---|
| Cliente móvil / web | Cámara, guía visual, captura, recaptura, envío y experiencia de usuario |
| API de validación | Calidad de imagen, OCR, parsing, comparación, almacenamiento, auditoría |
| Base de datos | Persistencia de documento, metadatos, resultado OCR, trazabilidad |
| Almacenamiento | Archivo original y futuras variantes derivadas |

## Flujo recomendado

El flujo más robusto para producción no debe enviar la foto directamente al OCR sin una validación previa. En su lugar, debe introducir un ciclo corto de control de calidad.

| Paso | Acción |
|---|---|
| 1 | El usuario abre la cámara desde app móvil o web app |
| 2 | El cliente muestra guía de encuadre y usa la cámara trasera si existe |
| 3 | El cliente toma la imagen y la envía a `POST /api/v1/documents/analyze-capture` |
| 4 | Si la calidad es baja, el cliente solicita recaptura antes de cargar el documento |
| 5 | Si la calidad es suficiente, el cliente invoca `POST /api/v1/documents/upload` |
| 6 | El backend almacena y registra la imagen |
| 7 | El cliente invoca `POST /api/v1/documents/{document_id}/process` |
| 8 | El backend ejecuta OCR, parsing y comparación |
| 9 | El cliente consulta `GET /api/v1/documents/{document_id}/results` |
| 10 | Si el resultado es aceptable, el cliente confirma; si no, solicita recaptura |

## Recomendaciones para app móvil

Para móvil, la prioridad debe ser maximizar la calidad de captura antes de enviar al backend. La aplicación debe abrir la cámara trasera, bloquear orientaciones no deseadas durante la captura, mostrar una máscara de documento, detectar poca luz y guiar al usuario para reducir brillo, reflejos y desenfoque.

## Recomendaciones para web app

Para web, la prioridad debe ser trabajar bien en navegadores móviles modernos. La interfaz debe solicitar cámara mediante APIs estándar del navegador, preferir la cámara trasera cuando el dispositivo lo permita y capturar una imagen fija de alta resolución. Si se añade rectificación local, la web app podrá mejorar la perspectiva antes del envío al backend.

## APIs futuras sugeridas

| Endpoint futuro | Objetivo |
|---|---|
| `POST /documents/analyze-capture` | Ya implementado, útil para control de calidad previo |
| `POST /documents/upload` | Ya implementado, persiste imagen y estado inicial |
| `POST /documents/{id}/process` | Ya implementado, ejecuta OCR y extracción |
| `POST /documents/{id}/retry` | Ya implementado, permite recaptura |
| `GET /documents/supported-types` | Útil para que el cliente consulte catálogos y reglas |
| `POST /documents/{id}/process-async` | Recomendado si el OCR crece en costo o tiempo |
| `GET /documents/{id}/events` | Recomendado para seguimiento fino del flujo |

## Decisiones de diseño ya preparadas en este repositorio

La versión actual del backend ya deja una base mucho mejor para esa evolución. El almacenamiento puede operar en local o GCS. El OCR puede operar con Tesseract o Google Vision. La base de datos puede operar con `DATABASE_URL`, incluyendo SQLite para pruebas locales. Además, el endpoint de análisis previo de captura permite desacoplar mejor el cliente de la lógica de persistencia.

## Próximos pasos recomendados

El siguiente salto de valor debería consistir en construir un cliente ligero de captura, primero como web app de pruebas y luego como app móvil o híbrida. Ese cliente no debe duplicar lógica de OCR ni de validación de negocio; debe enfocarse en capturar mejor la imagen y en guiar al usuario con la menor fricción posible.
