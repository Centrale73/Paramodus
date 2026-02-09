"use client"

import { cn } from "@/lib/utils"
import { ChevronDown } from "lucide-react"
import { useState, useRef, useEffect } from "react"

const AVAILABLE_MODELS = [
  { id: "llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
  { id: "llama-3.1-8b-instant", label: "Llama 3.1 8B" },
  { id: "mixtral-8x7b-32768", label: "Mixtral 8x7B" },
  { id: "gemma2-9b-it", label: "Gemma 2 9B" },
]

interface SettingsPanelProps {
  currentModel: string
  onModelChange: (model: string) => void
}

export function SettingsPanel({
  currentModel,
  onModelChange,
}: SettingsPanelProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const selectedModel = AVAILABLE_MODELS.find((m) => m.id === currentModel)

  return (
    <div className="flex flex-col gap-6">
      {/* Model Selection */}
      <div>
        <label className="block text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
          Model
        </label>
        <div ref={dropdownRef} className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className={cn(
              "w-full flex items-center justify-between px-3.5 py-3 rounded-xl",
              "bg-muted/50 border border-border/50 text-sm",
              "hover:border-primary/50 transition-colors",
              isDropdownOpen && "border-primary/50"
            )}
          >
            <span className="text-foreground">
              {selectedModel?.label || currentModel}
            </span>
            <ChevronDown
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isDropdownOpen && "rotate-180"
              )}
            />
          </button>

          {isDropdownOpen && (
            <div className="absolute top-full left-0 right-0 mt-1 z-50 rounded-xl border border-border/50 bg-card shadow-xl shadow-black/30 overflow-hidden">
              {AVAILABLE_MODELS.map((model) => (
                <button
                  key={model.id}
                  onClick={() => {
                    onModelChange(model.id)
                    setIsDropdownOpen(false)
                  }}
                  className={cn(
                    "w-full px-3.5 py-2.5 text-left text-sm transition-colors",
                    model.id === currentModel
                      ? "bg-primary/20 text-foreground"
                      : "text-foreground hover:bg-muted/50"
                  )}
                >
                  {model.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="rounded-xl border border-border/50 bg-muted/30 p-4">
        <p className="text-xs text-muted-foreground leading-relaxed">
          This workspace uses <span className="text-foreground font-medium">Groq</span> for fast
          AI inference. The API key is configured via the project&apos;s environment
          variables.
        </p>
      </div>
    </div>
  )
}
