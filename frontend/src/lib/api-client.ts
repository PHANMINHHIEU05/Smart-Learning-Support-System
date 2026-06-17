import { createSupabaseClient } from "./supabase";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const LEGACY_API_BASE = API_BASE;

export const SPRING_API_BASE =
  process.env.NEXT_PUBLIC_SPRING_API_URL ?? "http://localhost:8080";

const SPRING_API_PATH_PREFIXES = [
  "/api/v1/me",
  "/api/v1/tasks",
  "/api/v1/sessions",
  "/api/v1/blocks",
  "/api/v1/settings",
  "/api/v1/monitoring",
  "/api/v1/ai-events",
  "/api/v1/alerts",
];

const TOKEN_CACHE_MS = 15_000;
let cachedToken = "";
let cachedTokenAt = 0;
let inFlightTokenPromise: Promise<string> | null = null;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function getApiAccessToken(
  options?: { forceRefresh?: boolean },
): Promise<string> {
  const forceRefresh = options?.forceRefresh === true;
  const now = Date.now();

  if (!forceRefresh && cachedToken && now - cachedTokenAt < TOKEN_CACHE_MS) {
    return cachedToken;
  }

  if (!forceRefresh && inFlightTokenPromise) {
    return inFlightTokenPromise;
  }

  const supabase = createSupabaseClient();
  inFlightTokenPromise = supabase.auth
    .getSession()
    .then(({ data }) => {
      const token = data.session?.access_token ?? "";
      cachedToken = token;
      cachedTokenAt = Date.now();
      return token;
    })
    .catch(() => {
      cachedToken = "";
      cachedTokenAt = Date.now();
      return "";
    })
    .finally(() => {
      inFlightTokenPromise = null;
    });

  return inFlightTokenPromise;
}

function matchesApiPrefix(path: string, prefix: string): boolean {
  return (
    path === prefix ||
    path.startsWith(`${prefix}/`) ||
    path.startsWith(`${prefix}?`)
  );
}

export function getApiBaseForPath(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return "";
  }

  return SPRING_API_PATH_PREFIXES.some((prefix) =>
    matchesApiPrefix(path, prefix),
  )
    ? SPRING_API_BASE
    : LEGACY_API_BASE;
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = await getApiAccessToken();
  const apiBase = getApiBaseForPath(path);

  const res = await fetch(`${apiBase}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}
