"use client"

import { cn } from "@/lib/utils"
import { ArrowUp, Square } from "lucide-react"
import { useRef, useEffect } from "react"
import type { TypingMood } from "@/hooks/use-typing-speed"

const moodBorderMap: Record<TypingMood, string> = {
  slow: "border-indigo-400/60 shadow-indigo-500/20",
  neutral: "border-primary/50 shadow-primary/10",
  fast: "border-pink-400/60 shadow-pink-500/20",
}

const moodButtonMap: Record<TypingMood, string> = {
  slow: "bg-indigo-500 hover:shadow-indigo-500/40",
  neutral: "bg-primary hover:shadow-primary/40",
  fast: "bg-pink-500 hover:shadow-pink-500/40",
}

interface ChatInputProps {
  input: string
  onInputChange: (value: string) => void
  onSend: () => void
  onStop: () => void
  isLoading: boolean
  typingMood?: TypingMood
  onKeystroke?: () => void
}

export function ChatInput({
  input,
  onInputChange,
  onSend,
  onStop,
  isLoading,
  typingMood = "neutral",
  onKeystroke,
}: ChatInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleKeyDown(e: React.KeyboardEvent) {
    // Track typing speed for any character key or backspace
    if (e.key.length === 1 || e.key === "Backspace") {
      onKeystroke?.()
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (isLoading) return
      onSend()
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    const textarea = inputRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px"
    }
  }, [input])

  return (
    <div className="px-6 pb-6 pt-2">
      <div
        className={cn(
          "flex items-end gap-2 rounded-[1.75rem] px-2 py-1.5",
          "bg-card/50 backdrop-blur-xl border",
          "transition-all duration-500 ease-out",
          input.trim()
            ? `shadow-lg ${moodBorderMap[typingMood]}`
            : "border-border/50"
        )}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask your agent..."
          rows={1}
          className={cn(
            "flex-1 bg-transparent border-none outline-none resize-none",
            "py-3 px-4 text-[0.95rem] text-foreground",
            "placeholder:text-muted-foreground",
            "max-h-[200px]"
          )}
        />
        {isLoading ? (
          <button
            onClick={onStop}
            className={cn(
              "flex items-center justify-center w-11 h-11 rounded-full",
              "bg-destructive text-destructive-foreground",
              "hover:bg-destructive/90 transition-all duration-200",
              "shrink-0"
            )}
            title="Stop generating"
          >
            <Square className="h-4 w-4 fill-current" />
          </button>
        ) : (
          <button
            onClick={onSend}
            disabled={!input.trim()}
            className={cn(
              "flex items-center justify-center w-11 h-11 rounded-full",
              "text-primary-foreground",
              "hover:scale-105 hover:shadow-lg",
              "active:scale-95",
              "transition-all duration-500 ease-out",
              "disabled:opacity-40 disabled:hover:scale-100 disabled:hover:shadow-none",
              "shrink-0",
              moodButtonMap[typingMood]
            )}
            title="Send message"
          >
            <ArrowUp className="h-5 w-5" />
          </button>
        )}
      </div>
      {/* Mood indicator */}
      {input.trim() && typingMood !== "neutral" && (
        <div className="flex justify-center mt-2">
          <span
            className={cn(
              "text-[0.65rem] font-medium tracking-wider uppercase px-3 py-0.5 rounded-full transition-all duration-500",
              typingMood === "slow"
                ? "text-indigo-400/70 bg-indigo-500/10"
                : "text-pink-400/70 bg-pink-500/10"
            )}
          >
            {typingMood === "slow" ? "thoughtful" : "rapid"}
          </span>
        </div>
      )}
    </div>
  )
}
