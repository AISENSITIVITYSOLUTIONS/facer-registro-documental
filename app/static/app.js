const pretty = (value) => JSON.stringify(value, null, 2);
let cameraStream = null;
let capturedFile = null;

const setOutput = (elementId, value) => {
  document.getElementById(elementId).textContent =
    typeof value === "string" ? value : pretty(value);
};

const setCameraStatus = (value) => {
  document.getElementById("camera-status").textContent = value;
};

const stopCameraStream = () => {
  if (!cameraStream) {
    return;
  }

  cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  document.getElementById("camera-preview").srcObject = null;
  setCameraStatus("Camara cerrada");
};

const syncCapturedFileToInput = (file) => {
  const fileInput = document.getElementById("document-file");
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  fileInput.files = dataTransfer.files;
};

const parseResponse = async (response) => {
  const text = await response.text();

  try {
    const body = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new Error(pretty(body));
    }
    return body;
  } catch (error) {
    if (!response.ok) {
      throw new Error(text || response.statusText);
    }
    throw error;
  }
};

document.getElementById("camera-start").addEventListener("click", async () => {
  try {
    stopCameraStream();
    setCameraStatus("Solicitando acceso a la camara...");
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      },
      audio: false,
    });
    const preview = document.getElementById("camera-preview");
    const shot = document.getElementById("camera-shot");
    preview.hidden = false;
    shot.hidden = true;
    preview.srcObject = cameraStream;
    setCameraStatus("Camara activa. Centra el documento y captura.");
  } catch (error) {
    setCameraStatus(`No se pudo abrir la camara: ${error.message}`);
  }
});

document.getElementById("camera-capture").addEventListener("click", async () => {
  try {
    const preview = document.getElementById("camera-preview");
    if (!cameraStream || !preview.videoWidth || !preview.videoHeight) {
      throw new Error("Abre la camara antes de capturar.");
    }

    const canvas = document.getElementById("camera-canvas");
    canvas.width = preview.videoWidth;
    canvas.height = preview.videoHeight;

    const context = canvas.getContext("2d");
    context.drawImage(preview, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.95));
    if (!blob) {
      throw new Error("No se pudo generar la imagen capturada.");
    }

    capturedFile = new File([blob], `captura-documento-${Date.now()}.jpg`, {
      type: "image/jpeg",
    });
    syncCapturedFileToInput(capturedFile);

    const shot = document.getElementById("camera-shot");
    shot.src = URL.createObjectURL(blob);
    shot.hidden = false;
    preview.hidden = true;
    setCameraStatus("Captura lista. Puedes subirla al flujo documental.");
  } catch (error) {
    setCameraStatus(error.message);
  }
});

document.getElementById("camera-stop").addEventListener("click", () => {
  stopCameraStream();
});

document.getElementById("camera-clear").addEventListener("click", () => {
  capturedFile = null;
  document.getElementById("document-file").value = "";
  document.getElementById("camera-shot").hidden = true;
  document.getElementById("camera-preview").hidden = false;
  setCameraStatus("Captura limpiada");
});

document.getElementById("health-button").addEventListener("click", async () => {
  try {
    setOutput("health-output", "Consultando...");
    const response = await fetch("/health");
    setOutput("health-output", await parseResponse(response));
  } catch (error) {
    setOutput("health-output", error.message);
  }
});

document.getElementById("user-button").addEventListener("click", async () => {
  try {
    const userId = document.getElementById("user-id").value;
    setOutput("user-output", "Consultando...");
    const response = await fetch(`/api/v1/users/${userId}`);
    setOutput("user-output", await parseResponse(response));
  } catch (error) {
    setOutput("user-output", error.message);
  }
});

document.getElementById("upload-button").addEventListener("click", async () => {
  try {
    const form = document.getElementById("upload-form");
    const formData = new FormData(form);
    const fileInput = document.getElementById("document-file");

    if (!fileInput.files.length) {
      throw new Error("Selecciona una imagen antes de subir.");
    }

    setOutput("upload-output", "Subiendo...");
    const response = await fetch("/api/v1/documents/upload", {
      method: "POST",
      body: formData,
    });
    const body = await parseResponse(response);
    setOutput("upload-output", body);

    if (body.id) {
      document.getElementById("process-document-id").value = body.id;
      document.getElementById("results-document-id").value = body.id;
    }
  } catch (error) {
    setOutput("upload-output", error.message);
  }
});

document.getElementById("process-button").addEventListener("click", async () => {
  try {
    const documentId = document.getElementById("process-document-id").value;
    setOutput("process-output", "Procesando...");
    const response = await fetch(`/api/v1/documents/${documentId}/process`, {
      method: "POST",
    });
    setOutput("process-output", await parseResponse(response));
  } catch (error) {
    setOutput("process-output", error.message);
  }
});

document.getElementById("results-button").addEventListener("click", async () => {
  try {
    const documentId = document.getElementById("results-document-id").value;
    setOutput("results-output", "Consultando...");
    const response = await fetch(`/api/v1/documents/${documentId}/results`);
    setOutput("results-output", await parseResponse(response));
  } catch (error) {
    setOutput("results-output", error.message);
  }
});
