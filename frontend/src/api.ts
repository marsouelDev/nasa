export interface ApiError {
  message: string;
  status: number;
}

export async function fetchWithErrorHandling(
  endpoint: string,
  options: any = {}
): Promise<{ data: any; error: ApiError | null }> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        data: null,
        error: {
          message: errorData.message || response.statusText,
          status: response.status,
        },
      };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (error) {
    return {
      data: null,
      error: {
        message: error instanceof Error ? error.message : "Erreur de connexion",
        status: 0,
      },
    };
  }
}

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

export async function getZones(): Promise<{ zones: any[]; error: ApiError | null }> {
  const result = await fetchWithErrorHandling("/zones");
  return { zones: result.data?.zones || [], error: result.error };
}

export async function getPluie(zone: string, debut?: string, fin?: string): Promise<{
  data: any;
  error: ApiError | null
}> {
  const params = new URLSearchParams();
  if (debut) params.set("debut", debut);
  if (fin) params.set("fin", fin);
  return fetchWithErrorHandling(`/pluie?zone=${zone}&${params.toString()}`);
}

export async function getRisques(zone: string, culture?: string): Promise<{
  data: any;
  error: ApiError | null
}> {
  const params = new URLSearchParams();
  if (culture) params.set("culture", culture);
  return fetchWithErrorHandling(`/risques?zone=${zone}&${params.toString()}`);
}

export async function getCalendrierSemis(zone: string, annee?: number): Promise<{
  data: any;
  error: ApiError | null
}> {
  const params = new URLSearchParams();
  if (annee) params.set("annee", String(annee));
  return fetchWithErrorHandling(`/calendrier-semis?zone=${zone}&${params.toString()}`);
}

export async function getPoint(lat: number, lon: number): Promise<{
  data: any;
  error: ApiError | null
}> {
  return fetchWithErrorHandling(`/point?lat=${lat}&lon=${lon}`);
}