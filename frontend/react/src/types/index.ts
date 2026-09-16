export type User = { id: number; username: string; role: "admin" | "editor" | "viewer"; created_at?: string; };
export type Channel = { id: number; channel_number?: number | null; name: string; url: string; logo?: string; metadata?: string; tvg_id?: string; group_title?: string; country?: string; state?: string; city?: string; category: string; status: string; latency_ms?: number; auto_remove_if_offline?: number; playlist?: string; xmltv_file?: string; };
export type Manifest = { m3u_name: string; m3u_url: string; xml_name?: string; xml_url: string; total: number; };
export type Status = { status: string; total_canais: number; canais_online: number; canais_offline: number; canais_desconhecidos?: number; ultimo_log: string; logs: { timestamp: string; level: string; message: string }[]; log_count: number; };
export type ChannelOptions = { country: string[]; state: string[]; city: string[]; category: string[]; status: string[]; };
export type InternetHealth = { online: boolean; target: string; host: string; latency_ms: number; interval_seconds?: number; timeout_seconds?: number; error?: string; };
export type ChannelColumn = "status" | "id" | "logo" | "name" | "country" | "state" | "city" | "playlist" | "group_title" | "xmltv_file" | "tvg_id" | "latency_ms" | "auto_remove" | "actions";
