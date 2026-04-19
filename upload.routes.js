const express = require('express');
const multer = require('multer');
const { uploadFile } = require('./gcs');

const router = express.Router();

const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: parseInt(process.env.MAX_UPLOAD_SIZE_BYTES),
  },
});

router.post('/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const result = await uploadFile(
      req.file.buffer,
      req.file.originalname,
      req.file.mimetype
    );

    res.json({
      message: 'File uploaded successfully',
      data: result,
    });

  } catch (error) {
    console.error(error);
    res.status(500).json({
      error: 'Upload failed',
    });
  }
});

module.exports = router;
