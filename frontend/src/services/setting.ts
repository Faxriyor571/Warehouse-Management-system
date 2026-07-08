import { http } from "@/lib/http";
import type { SettingsMap } from "@/types/setting";

export const settingService = {
  async get(): Promise<SettingsMap> {
    const { data } = await http.get<SettingsMap>("/settings");
    return data;
  },

  async upsert(key: string, value: string | null): Promise<SettingsMap> {
    const { data } = await http.put<SettingsMap>("/settings", { key, value });
    return data;
  },
};
