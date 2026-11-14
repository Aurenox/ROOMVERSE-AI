export type Gender = "male" | "female" | "others";
export type Scene = {id: string; title: string; location: string; difficulty: string; duration: string};
export type Exhibit = [string, string];
export type Phase = "observe" | "quiz" | "complete";
export type Game = {
  id: string; game_id: string; title: string; difficulty: string; intro: string;
  objective: string; source: string; phase: Phase; position: number; score: number;
  hints_remaining: number; deadline: string | null; server_time: string;
  story_title?: string; has_change_round?: boolean; exhibits?: Exhibit[]; hints?: string[];
  question?: {question: string; options: string[]; evidence?: Exhibit[]; changed_image?: string};
  completion?: string; hints_used?: number; correct?: number; elapsed?: number;
  practice_only?: boolean; leaderboard_difficulty?: string | null; character?: Gender; rank_score?: number; detective_name?: string; detective_title?: string; leaderboard_rank?: number | null;
  review?: {submitted: string; correct: boolean; question: string; answer: string; explanation: string; changed_image?: string | null}[];
};
export type Home = {
  scenes: Scene[]; themes: string[]; difficulty: string[]; ai_configured: boolean;
  profile: {username: string; avatar: string; gender: Gender; voice_style: string; voice_rate: number; public_score: boolean} | null; xp: number; level: number; badges: string[];
  history: {id: string; title: string; phase: Phase; score: number}[];
  scans: {id: string; created: string}[];
};
export type Scan = {id: string; source: string; privacy_status?: "checked" | "unavailable"; objects: {id: string; name: string; description: string; confidence_label: string; usable_for_puzzle: boolean}[]};

export async function api<T>(path = "", method = "GET", data?: object): Promise<T> {
  const csrf = document.cookie.split("; ").find(cookie => cookie.startsWith("csrftoken="))?.split("=")[1] || "";
  const headers: Record<string, string> = {"X-CSRFToken": csrf};
  if (!(data instanceof FormData) && data) headers["Content-Type"] = "application/json";
  const response = await fetch(`/api/${path}`, {
    method, headers, credentials: "same-origin", cache: "no-store",
    body: data instanceof FormData ? data : data ? JSON.stringify(data) : undefined,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "The case server could not complete the request. Try again.");
  }
  return response.status === 204 ? undefined as T : response.json();
}
