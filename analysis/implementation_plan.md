# Plan técnico de mejora para `facer-registro-documental`

## Objetivo

El objetivo de la siguiente iteración es transformar el backend actual, que hoy está acoplado a Google Cloud Storage, Google Cloud Vision y MySQL, en una base técnica más apta para desarrollo local, evolución a servicio profesional y futura integración con una app móvil o web app de captura documental.

## Diagnóstico resumido

El proyecto actual funciona como backend de procesamiento documental, pero no incluye front-end ni cliente móvil. La captura depende por completo de la calidad de la imagen que el cliente suba. El almacenamiento está acoplado a GCS, el OCR a Google Vision y la persistencia a MySQL. Además, existe al menos un defecto funcional claro en la confirmación documental: la lógica compara un enum con cadenas literales, lo que impide que ciertos documentos pasen correctamente a estado válido.

| Área | Estado actual | Riesgo | Mejora propuesta |
|---|---|---|---|
| Captura | No existe cliente de cámara ni guía de captura | Alta tasa de recaptura y OCR inconsistente | Preparar API más adecuada para clientes web/móvil y documentar estrategia de captura |
| Calidad de imagen | Solo mide brillo, contraste, nitidez, glare y resolución | No corrige perspectiva, rotación ni mejora OCR | Agregar preprocesamiento configurable antes del OCR |
| OCR | Solo Google Vision | Dependencia externa, costo y falta de modo local | Crear servicio OCR desacoplado con soporte local y configurable |
| Almacenamiento | Solo GCS | No sirve bien para modo local | Agregar backend local de archivos y abstraer URI de almacenamiento |
| Base de datos | Solo MySQL vía configuración | Más fricción para desarrollo local | Permitir SQLite local como opción de desarrollo |
| Modelo de datos/API | Acoplado semánticamente a GCS | Dificulta evolución | Generalizar nombres hacia URI de almacenamiento |
| Validación de negocio | Parsing heurístico básico | Extracciones débiles para documentos reales | Fortalecer parsing y normalización por tipo documental |
| Confirmación | Bug enum vs string | Estados incorrectos | Corregir lógica |
| Calidad de ingeniería | Sin pruebas automatizadas visibles | Riesgo de regresiones | Agregar pruebas de parsing y servicios críticos |

## Cambios a implementar en código

En la siguiente fase se implementarán los cambios más rentables y seguros dentro del repositorio actual.

Primero, se introducirá una **capa de almacenamiento configurable** con al menos dos backends: almacenamiento local en sistema de archivos para desarrollo y almacenamiento GCS para compatibilidad con nube. El sistema dejará de depender semánticamente de `source_image_gcs_path` y pasará a una representación más general de URI.

Segundo, se introducirá una **capa OCR configurable**. Se mantendrá compatibilidad con Google Vision, pero se añadirá un camino local basado en un motor open source. La meta no es reemplazar por completo todos los flujos avanzados, sino habilitar una operación profesional local y desacoplada.

Tercero, se incorporará un **preprocesamiento de imagen** antes del OCR, orientado a mejorar legibilidad: normalización de contraste, escala de grises, autocontraste, filtrado y variantes de imagen. Esto permitirá intentar OCR sobre una versión más limpia que la imagen cruda.

Cuarto, se corregirá el **bug de validación** en la confirmación documental y se reforzarán las heurísticas de parsing para INE, pasaportes y cédulas, especialmente en nombres, MRZ y normalización de identificadores.

Quinto, se facilitará el **desarrollo local** habilitando SQLite como backend de base de datos opcional y actualizando la configuración y documentación para que el servicio pueda levantarse sin dependencia obligatoria de Google Cloud.

Sexto, se agregarán **pruebas automatizadas** sobre parsing, comparación y decisiones de negocio críticas.

## Ruta recomendada para cliente futuro

| Cliente futuro | Recomendación técnica |
|---|---|
| Android / app móvil híbrida | Usar un flujo de captura guiada o scanner del sistema, idealmente con auto-detección de documento, recorte y limpieza antes del envío |
| Web app | Usar cámara del navegador, selección de cámara trasera, captura de still y rectificación de perspectiva antes de enviar al backend |
| Backend/API | Mantener API centrada en validación, OCR, parsing, comparación y auditoría, evitando lógica de UI dentro del servicio |
| Extracción avanzada futura | Evaluar especialización por tipo documental y modelos afinados para INE, cédula colombiana y pasaportes |

## Criterio de implementación

Se priorizarán cambios que mejoren de forma inmediata la operatividad local, reduzcan acoplamiento, suban la calidad del OCR y dejen una base profesional para evolucionar después a aplicación móvil o web sin rehacer el backend.
