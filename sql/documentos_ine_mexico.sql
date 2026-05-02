-- Create the documentos_ine_mexico table
-- This table stores extracted INE data with all relevant fields

CREATE TABLE IF NOT EXISTS documentos_ine_mexico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre VARCHAR(120) DEFAULT NULL,
    apellido_paterno VARCHAR(120) DEFAULT NULL,
    apellido_materno VARCHAR(120) DEFAULT NULL,
    nombre_completo VARCHAR(250) DEFAULT NULL,
    nacionalidad VARCHAR(60) DEFAULT NULL,
    fecha_nacimiento DATE DEFAULT NULL,
    curp VARCHAR(18) DEFAULT NULL,
    domicilio TEXT DEFAULT NULL,
    ocr_texto_original TEXT DEFAULT NULL,
    ocr_confianza FLOAT DEFAULT NULL,
    imagen_frontal_url VARCHAR(500) DEFAULT NULL,
    fecha_captura DATETIME DEFAULT NULL,
    creado_por VARCHAR(100) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_usuario_id (usuario_id),
    INDEX idx_curp (curp),
    INDEX idx_created_at (created_at),
    CONSTRAINT fk_ine_usuario FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
