/** Cliente HTTP central da SPA. */
export const api = async <T,>(url: string, options?: RequestInit): Promise<T> => { const response = await fetch(url, options); if (!response.ok) throw new Error(String(response.status)); return response.json() as Promise<T>; };
export const send = <T = unknown,>(url: string, body?: unknown) => api<T>(url, { method: "POST", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
