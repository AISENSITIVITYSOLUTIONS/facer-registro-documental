# Hallazgos desde revisión web

## Repositorio `facer-registro-documental`

El repositorio publicado en GitHub se presenta como un backend FastAPI para validación documental. Declara soporte para OCR con Google Cloud Vision, almacenamiento privado en Google Cloud Storage, comparación contra un registro institucional y persistencia en MySQL. En la vista del repositorio no aparecen componentes de front-end web, app móvil ni clientes de captura con cámara.

## ML Kit Document Scanner

La documentación oficial de Google ML Kit indica que el document scanner ofrece una experiencia de captura de documentos de alta calidad para Android, con captura automática, detección precisa de bordes, rotación automática, recorte, filtros, eliminación de sombras y manchas, y flujo completo en dispositivo. También indica que el procesamiento ocurre on-device, con bajo impacto en tamaño binario y sin requerir permiso de cámara directo desde la app porque el flujo aprovecha Google Play Services.

## Implicación arquitectónica preliminar

Para una evolución hacia app móvil profesional, el flujo actual del backend debería complementarse con una capa cliente de captura guiada. En Android, ML Kit Document Scanner parece una opción fuerte para preprocesar mejor la imagen antes de enviarla al backend de OCR y extracción.

## PaddleOCR Document Image Preprocessing

La documentación oficial de PaddleOCR describe un pipeline de preprocesamiento documental con dos funciones principales: clasificación de orientación del documento y corrección de distorsión geométrica. El módulo de orientación identifica 0°, 90°, 180° y 270°, y el módulo de unwarping corrige deformaciones geométricas producidas por fotografía o escaneo. El pipeline está pensado como base para OCR y despliegue orientado a servicio, y además permite ajuste fino con datasets propios.

## docTR

La documentación oficial de docTR lo presenta como un OCR open source de dos etapas, detección y reconocimiento, con parámetros preentrenados, enfoque en inferencia CPU/GPU, dependencias ligeras y plantillas de integración para demostración en navegador y despliegue como API. La documentación afirma rendimiento de estado del arte sobre datasets públicos y comparabilidad con Google Vision y AWS Textract en escenarios documentales.

## Implicación arquitectónica preliminar adicional

Hay una ruta sólida para un rediseño híbrido y profesional:

1. Captura guiada o escaneo automático en cliente móvil/web.
2. Preprocesamiento geométrico y de orientación previo al OCR.
3. OCR desacoplado mediante motor configurable.
4. Parsing específico por tipo documental con reglas y validaciones.
5. Persistencia local o compatible con nube sin acoplar el esquema a un proveedor concreto.

## Captura web con `getUserMedia`

La documentación de MDN confirma que `navigator.mediaDevices.getUserMedia()` permite solicitar vídeo desde la cámara y entrega un `MediaStream`, pero solo funciona en contextos seguros (HTTPS) y depende del permiso explícito del usuario. Esto confirma que una futura web app puede capturar imagen desde cámara nativa del navegador, aunque requiere diseñar adecuadamente permisos, selección de cámara y manejo de errores del dispositivo.

## Rectificación de imagen con OpenCV.js

La documentación oficial de OpenCV.js confirma soporte para transformaciones geométricas y, en particular, `cv.getPerspectiveTransform()` y `cv.warpPerspective()` para corregir perspectiva a partir de cuatro puntos sobre la imagen. Esto valida una ruta técnica viable para una web app que detecte un documento en cámara o fotografía y lo rectifique antes de enviarlo al backend de OCR.

## Implicación arquitectónica adicional

Para web app profesional, la combinación de captura con `getUserMedia` y rectificación con OpenCV.js permitiría construir un flujo de captura local en navegador con mejor calidad de imagen, menor tasa de OCR fallido y menos dependencia de recapturas manuales.
