/** Cliente HTTP central da SPA com tratamento de erros da API. */
export class ApiError extends Error {
    status: number;
    code?: string;
    resource?: string;
    action?: string;

    constructor(status: number, message: string, details: Record<string, unknown> = {}) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = typeof details.code === "string" ? details.code : undefined;
        this.resource = typeof details.resource === "string" ? details.resource : undefined;
        this.action = typeof details.action === "string" ? details.action : undefined;
    }
}

export const api = async <T,>(url: string, options?: RequestInit): Promise<T> => {
    let response: Response;
    try {
        response = await fetch(url, options);
    } catch {
        throw new ApiError(0, "Não foi possível conectar ao servidor.");
    }

    const contentType = response.headers.get("content-type") || "";
    let payload: unknown = null;
    if (contentType.includes("application/json")) {
        try { payload = await response.json(); } catch { payload = null; }
    } else {
        try { payload = await response.text(); } catch { payload = null; }
    }

    if (!response.ok) {
        const details = (payload && typeof payload === "object") ? payload as Record<string, unknown> : {};
        const message = typeof details.error === "string"
            ? details.error
            : typeof details.message === "string"
                ? details.message
                : `Falha na requisição (HTTP ${response.status}).`;
        throw new ApiError(response.status, message, details);
    }

    return payload as T;
};

export const send = <T = unknown,>(url: string, body?: unknown) => api<T>(url, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
});
