export const HOT_CITIES = ["成都", "广州", "武汉"] as const;

const KNOWN = new Set<string>(HOT_CITIES);

export function normalizeCityName(raw: string) {
  return raw.replace(/市$/, "").trim();
}

export function isKnownCity(raw: string) {
  return KNOWN.has(normalizeCityName(raw));
}
