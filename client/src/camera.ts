// Camera utilities for document capture

export interface CameraInstance {
  video: HTMLVideoElement;
  stream: MediaStream;
  stop: () => void;
  capture: (quality?: number) => Blob | null;
}

export async function startCamera(
  videoElement: HTMLVideoElement,
  facingMode: "user" | "environment" = "environment",
): Promise<CameraInstance> {
  const constraints: MediaStreamConstraints = {
    video: {
      facingMode,
      width: { ideal: 1920 },
      height: { ideal: 1080 },
    },
    audio: false,
  };

  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  videoElement.srcObject = stream;
  await videoElement.play();

  return {
    video: videoElement,
    stream,
    stop() {
      stream.getTracks().forEach((t) => t.stop());
      videoElement.srcObject = null;
    },
    capture(quality = 0.92): Blob | null {
      const canvas = document.createElement("canvas");
      canvas.width = videoElement.videoWidth;
      canvas.height = videoElement.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;
      ctx.drawImage(videoElement, 0, 0);
      // Convert to blob synchronously via dataURL
      const dataUrl = canvas.toDataURL("image/jpeg", quality);
      return dataUrlToBlob(dataUrl);
    },
  };
}

function dataUrlToBlob(dataUrl: string): Blob {
  const parts = dataUrl.split(",");
  const mime = parts[0].match(/:(.*?);/)![1];
  const bstr = atob(parts[1]);
  const u8arr = new Uint8Array(bstr.length);
  for (let i = 0; i < bstr.length; i++) {
    u8arr[i] = bstr.charCodeAt(i);
  }
  return new Blob([u8arr], { type: mime });
}
