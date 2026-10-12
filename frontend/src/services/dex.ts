import { api } from "@/services/api";
import type { Item, Move, Pokemon, SearchResult } from "@/types/dex";

export const dexApi = {
  async search(q: string, signal?: AbortSignal): Promise<SearchResult[]> {
    const { data } = await api.get<{ results: SearchResult[] }>("/dex/search", { params: { q }, signal });
    return data.results;
  },
  async pokemon(slug: string): Promise<Pokemon> {
    return (await api.get<Pokemon>(`/dex/pokemon/${slug}`)).data;
  },
  async move(slug: string): Promise<Move> {
    return (await api.get<Move>(`/dex/move/${slug}`)).data;
  },
  async item(slug: string): Promise<Item> {
    return (await api.get<Item>(`/dex/item/${slug}`)).data;
  },
};
