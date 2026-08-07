const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = "Something went wrong while processing your request.";

    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      // Keep the default message when the response body is not JSON.
    }

    throw new Error(detail);
  }

  return response.json();
}

export async function fetchExamples() {
  const response = await fetch(`${API_BASE_URL}/examples`);
  return handleResponse(response);
}

export async function searchMaterialIds(query) {
  const response = await fetch(`${API_BASE_URL}/materials/search?query=${encodeURIComponent(query)}`);
  return handleResponse(response);
}

export async function predictFromMaterialId(materialId) {
  const response = await fetch(`${API_BASE_URL}/predict/material/${materialId}`);
  return handleResponse(response);
}

export async function predictFromUpload(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/predict/upload`, {
    method: "POST",
    body: formData,
  });

  return handleResponse(response);
}
