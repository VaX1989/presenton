export const DEFAULT_MAX_NUMBER_OF_SLIDES = 100;
export let MAX_NUMBER_OF_SLIDES = DEFAULT_MAX_NUMBER_OF_SLIDES;
export const MAX_OUTLINE_CONTENT_WORDS = 100;

let MAX_SLIDES_SOURCE: "default" | "fastapi" = "default";

const WORD_PATTERN = /\S+/g;

export function setMaxNumberOfSlidesFromCapability(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0 || !Number.isInteger(parsed)) {
    throw new Error("FastAPI max_slides capability must be a positive integer");
  }
  MAX_NUMBER_OF_SLIDES = parsed;
  MAX_SLIDES_SOURCE = "fastapi";
  return MAX_NUMBER_OF_SLIDES;
}

export function getMaxSlidesSource(): "default" | "fastapi" {
  return MAX_SLIDES_SOURCE;
}

export function countOutlineWords(value: string): number {
  return value.match(WORD_PATTERN)?.length ?? 0;
}

export function trimTextToWordLimit(
  value: string,
  maxWords = MAX_OUTLINE_CONTENT_WORDS
): string {
  if (maxWords <= 0) return "";

  const matches = Array.from((value || "").matchAll(WORD_PATTERN));
  if (matches.length <= maxWords) return value;

  const lastMatch = matches[maxWords - 1];
  const endIndex = (lastMatch.index ?? 0) + lastMatch[0].length;
  return value.slice(0, endIndex).trimEnd();
}

export function limitOutlines<T extends { content?: unknown }>(
  outlines: T[] | null | undefined
): { content: string }[] {
  if (!Array.isArray(outlines)) return [];

  return outlines.slice(0, MAX_NUMBER_OF_SLIDES).map((outline) => ({
    ...outline,
    content: trimTextToWordLimit(
      typeof outline?.content === "string"
        ? outline.content
        : String(outline?.content ?? "")
    ),
  }));
}

export function clampSlideCountValue(value: string): string {
  const digitsOnly = value.replace(/\D+/g, "");
  if (!digitsOnly) return "";

  const normalized = digitsOnly.replace(/^0+/, "");
  if (!normalized) return "";

  return String(Math.min(Number(normalized), MAX_NUMBER_OF_SLIDES));
}

export function parseLimitedSlideCount(
  value: string | null | undefined
): number | null {
  if (!value || !/^\d+$/.test(value)) return null;

  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;

  return Math.min(parsed, MAX_NUMBER_OF_SLIDES);
}
