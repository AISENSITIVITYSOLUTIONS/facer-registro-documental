// Image compression utility for mobile uploads
// Resizes and compresses images to reduce upload time on slow connections

export interface CompressOptions {
  /** Maximum width in pixels (default: 1600) */
  maxWidth?: number;
  /** Maximum height in pixels (default: 1200) */
  maxHeight?: number;
  /** JPEG quality 0-1 (default: 0.82) */
  quality?: number;
  /** Maximum file size in bytes. If exceeded, quality is reduced iteratively (default: 1.5MB) */
  maxSizeBytes?: number;
}

export interface CompressResult {
  blob: Blob;
  originalSize: number;
  compressedSize: number;
  width: number;
  height: number;
  quality: number;
  compressionRatio: number;
}

/**
 * Compress an image blob for upload.
 * - Resizes to fit within maxWidth x maxHeight while maintaining aspect ratio
 * - Compresses as JPEG with iterative quality reduction if needed
 * - Ensures minimum resolution of 900x600 for backend requirements
 */
export async function compressImage(
  blob: Blob,
  options: CompressOptions = {},
): Promise<CompressResult> {
  const {
    maxWidth = 1600,
    maxHeight = 1200,
    quality: initialQuality = 0.82,
    maxSizeBytes = 1.5 * 1024 * 1024, // 1.5MB
  } = options;

  const originalSize = blob.size;

  // Load image from blob
  const img = await loadImage(blob);
  const origW = img.naturalWidth;
  const origH = img.naturalHeight;

  // Calculate target dimensions (maintain aspect ratio)
  let targetW = origW;
  let targetH = origH;

  if (targetW > maxWidth) {
    targetH = Math.round(targetH * (maxWidth / targetW));
    targetW = maxWidth;
  }
  if (targetH > maxHeight) {
    targetW = Math.round(targetW * (maxHeight / targetH));
    targetH = maxHeight;
  }

  // Ensure minimum resolution for backend (900x600)
  if (targetW < 900 || targetH < 600) {
    // Don't downscale below minimum
    targetW = Math.max(targetW, origW);
    targetH = Math.max(targetH, origH);
  }

  // Draw to canvas at target size
  const canvas = document.createElement("canvas");
  canvas.width = targetW;
  canvas.height = targetH;
  const ctx = canvas.getContext("2d")!;

  // Use high-quality resampling
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(img, 0, 0, targetW, targetH);

  // Iterative compression: reduce quality until under maxSizeBytes
  let quality = initialQuality;
  let resultBlob = await canvasToBlob(canvas, quality);

  const minQuality = 0.5; // Don't go below 50% quality
  while (resultBlob.size > maxSizeBytes && quality > minQuality) {
    quality -= 0.08;
    resultBlob = await canvasToBlob(canvas, quality);
  }

  return {
    blob: resultBlob,
    originalSize,
    compressedSize: resultBlob.size,
    width: targetW,
    height: targetH,
    quality,
    compressionRatio: originalSize > 0 ? resultBlob.size / originalSize : 1,
  };
}

function loadImage(blob: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(img.src);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(img.src);
      reject(new Error("No se pudo cargar la imagen"));
    };
    img.src = URL.createObjectURL(blob);
  });
}

function canvasToBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error("No se pudo comprimir la imagen"));
      },
      "image/jpeg",
      quality,
    );
  });
}

/**
 * Format bytes to human-readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
