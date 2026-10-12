import axios, { AxiosError } from "axios";
import { ChatRequest, ChatResponse, HealthResponse } from "@/types/chat";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const chatApi = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await api.post<ChatResponse>("/chat", request);
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<{ detail: string }>;
      throw new Error(
        axiosError.response?.data?.detail || "Failed to send message"
      );
    }
  },

  async checkHealth(): Promise<HealthResponse> {
    try {
      const response = await api.get<HealthResponse>("/health");
      return response.data;
    } catch {
      throw new Error("Backend server is offline");
    }
  },

  async getHistory(sessionId: string, limit: number = 10) {
    try {
      const response = await api.get(`/history/${sessionId}`, {
        params: { limit },
      });
      return response.data;
    } catch {
      throw new Error("Failed to fetch history");
    }
  },

  async getStats() {
    try {
      const response = await api.get("/stats");
      return response.data;
    } catch {
      throw new Error("Failed to fetch stats");
    }
  },
};
