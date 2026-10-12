export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  intent?: string;
  confidence?: number;
}

export interface ChatRequest {
  message: string;
  session_id?: string | null;
  use_fallback?: boolean;
}

export interface ChatResponse {
  message: string;
  intent: string;
  confidence: number;
  timestamp: string;
  session_id: string;
  source: "pokedex" | "knowledge" | "llm" | "database" | "default" | null;
  used_fallback: boolean;
  fallback_reason: string | null;
}

export interface HealthResponse {
  status: string;
  chatbot_ready: boolean;
  llm_fallback_ready: boolean;
  timestamp: string;
}
