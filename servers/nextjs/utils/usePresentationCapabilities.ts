"use client";

import { useEffect, useState } from "react";
import {
  DEFAULT_MAX_NUMBER_OF_SLIDES,
  setMaxNumberOfSlidesFromCapability,
} from "@/utils/presentationLimits";

export type PresentationCapabilities = {
  available: boolean;
  source: "fastapi" | "backend-unavailable" | "loading";
  maxSlides: number;
  strictMaterializeSupported: boolean;
  speakerNotesSupported: boolean;
  error?: string;
};

const INITIAL: PresentationCapabilities = {
  available: false,
  source: "loading",
  maxSlides: DEFAULT_MAX_NUMBER_OF_SLIDES,
  strictMaterializeSupported: false,
  speakerNotesSupported: false,
};

export function usePresentationCapabilities(): PresentationCapabilities {
  const [capabilities, setCapabilities] = useState<PresentationCapabilities>(INITIAL);

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch("/api/scientific-capabilities", {
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
        });
        const data = await response.json();
        if (!response.ok || !data.available) {
          setCapabilities({
            ...INITIAL,
            source: "backend-unavailable",
            error: data.detail || `capability request failed (${response.status})`,
          });
          return;
        }
        const maxSlides = setMaxNumberOfSlidesFromCapability(data.max_slides);
        setCapabilities({
          available: true,
          source: "fastapi",
          maxSlides,
          strictMaterializeSupported: Boolean(data.strict_materialize_supported),
          speakerNotesSupported: Boolean(data.speaker_notes_supported),
        });
      } catch (error) {
        if (controller.signal.aborted) return;
        setCapabilities({
          ...INITIAL,
          source: "backend-unavailable",
          error: error instanceof Error ? error.message : "capability request failed",
        });
      }
    })();
    return () => controller.abort();
  }, []);

  return capabilities;
}
