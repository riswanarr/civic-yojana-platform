const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const apiClient = {
  baseUrl: API_BASE_URL,

  async get<T>(path: string, accessToken?: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: accessToken
        ? {
            Authorization: `Bearer ${accessToken}`
          }
        : undefined
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || "Request failed.");
    }

    return response.json() as Promise<T>;
  }
};
