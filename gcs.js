console.log('BUCKET:', process.env.GCS_BUCKET_NAME);
const { Storage } = require('@google-cloud/storage');

const storage = new Storage({
  projectId: process.env.GCP_PROJECT_ID,
});

const bucket = storage.bucket(process.env.GCS_BUCKET_NAME);

const uploadFile = async (fileBuffer, fileName, mimeType) => {
  try {
    const filePath = `${process.env.GCS_DOCUMENTS_PREFIX}/${Date.now()}-${fileName}`;
    const file = bucket.file(filePath);

    await file.save(fileBuffer, {
      metadata: {
        contentType: mimeType,
      },
      resumable: false,
    });

    // URL pública (opcional)
    const publicUrl = `https://storage.googleapis.com/${process.env.GCS_BUCKET_NAME}/${filePath}`;

    return {
      success: true,
      filePath,
      publicUrl,
    };
  } catch (error) {
    console.error('Error uploading to GCS:', error);
    throw error;
  }
};

module.exports = {
  uploadFile,
};
