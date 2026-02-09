"use client"

import { cn } from "@/lib/utils"
import { ArrowUp, Square } from "lucide-react"
import { useRef, useEffect } from "react"

interface ChatInputProps {
  input: string
  onInputChange: (value: string) => void
  onSend: () => void
  onStop: () => void
  isLoading: boolean
}

export function ChatInput({
  input,
  onInputChange,
  onSend,
  onStop,
  isLoading,
}: ChatInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleKeyDown(e: React.KeyboardEvent) {
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
          "bg-card/50 backdrop-blur-xl border border-border/50",
          "transition-all duration-200",
          "focus-within:border-primary/50 focus-within:shadow-lg focus-within:shadow-primary/10"
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
              "bg-primary text-primary-foreground",
              "hover:scale-105 hover:shadow-lg hover:shadow-primary/40",
              "active:scale-95",
              "transition-all duration-200",
              "disabled:opacity-40 disabled:hover:scale-100 disabled:hover:shadow-none",
              "shrink-0"
            )}
            title="Send message"
          >
            <ArrowUp className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  )
}
