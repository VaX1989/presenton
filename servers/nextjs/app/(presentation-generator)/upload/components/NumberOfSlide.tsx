import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { clampSlideCountValue } from '@/utils/presentationLimits';
import { usePresentationCapabilities } from '@/utils/usePresentationCapabilities';
import React, { useEffect, useState } from 'react'

const SLIDE_OPTIONS: string[] = ["5", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"];

const NumberOfSlide = ({ value, onValueChange }: { value: string, onValueChange: (value: string) => void }) => {
    const capabilities = usePresentationCapabilities();
    const [customInput, setCustomInput] = useState(
        value && !SLIDE_OPTIONS.includes(value) ? value : ""
    );

    useEffect(() => {
        if (!capabilities.available) return;
        const numeric = Number(value);
        if (Number.isFinite(numeric) && numeric > capabilities.maxSlides) {
            const clamped = String(capabilities.maxSlides);
            onValueChange(clamped);
            setCustomInput(clamped);
        }
    }, [capabilities.available, capabilities.maxSlides, onValueChange, value]);

    const sanitizeToPositiveInteger = (raw: string): string => {
        return clampSlideCountValue(raw);
    };

    const applyCustomValue = () => {
        const sanitized = sanitizeToPositiveInteger(customInput);
        if (sanitized && Number(sanitized) > 0) {
            onValueChange(sanitized);
        }
    };
    return (
        <Select value={value || ""} onValueChange={onValueChange} name="slides">
            <SelectTrigger
                className="w-[180px] font-manrope font-medium bg-blue-100 border-blue-200 focus-visible:ring-blue-300"
                data-testid="slides-select"
            >
                <SelectValue placeholder="Select Slides" />
            </SelectTrigger>
            <SelectContent className="font-manrope">
                <div
                    className="sticky top-0 z-10 bg-white p-2 border-b"
                    onMouseDown={(e) => e.stopPropagation()}
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="flex items-center gap-2">
                        <Input
                            inputMode="numeric"
                            pattern="[0-9]*"
                            max={capabilities.maxSlides}
                            value={customInput}
                            onMouseDown={(e) => e.stopPropagation()}
                            onPointerDown={(e) => e.stopPropagation()}
                            onClick={(e) => e.stopPropagation()}
                            onChange={(e) => {
                                const next = sanitizeToPositiveInteger(e.target.value);
                                setCustomInput(next);
                            }}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                    e.preventDefault();
                                    applyCustomValue();
                                }
                            }}
                            onBlur={applyCustomValue}
                            placeholder="--"
                            className="h-8 w-16 px-2 text-sm"
                        />
                        <span className="text-sm font-medium">slides</span>
                    </div>
                    <div
                        className="mt-1 text-[10px] text-slate-500"
                        title={capabilities.error}
                        data-capability-source={capabilities.source}
                    >
                        max {capabilities.maxSlides} · {capabilities.source === "fastapi" ? "server capability" : "fallback until server responds"}
                    </div>
                </div>

                {value && !SLIDE_OPTIONS.includes(value) && (
                    <SelectItem value={value} className="hidden">
                        {value} slides
                    </SelectItem>
                )}

                {SLIDE_OPTIONS.map((option) => (
                    <SelectItem
                        key={option}
                        value={option}
                        className="font-manrope text-sm font-medium"
                        role="option"
                    >
                        {option} slides
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    )
}

export default NumberOfSlide
