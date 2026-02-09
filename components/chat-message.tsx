"use client"

import { cn } from "@/lib/utils"
import type { UIMessage } from "ai"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

function getMessageText(message: UIMessage): string {
  if (!message.parts || !Array.isArray(message.parts)) return ""
  return message.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("")
}

interface ChatMessageProps {
  message: UIMessage
  isStreaming?: boolean
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const text = getMessageText(message)
  const isUser = message.role === "user"

  return (
    <div
      className={cn(
        "flex flex-col max-w-[80%] animate-message-in",
        isUser ? "self-end items-end" : "self-start items-start"
      )}
    >
      <div
        className={cn(
          "px-5 py-3.5 rounded-2xl text-[0.95rem] leading-relaxed break-words",
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm shadow-lg shadow-primary/25"
            : "bg-card/50 text-foreground rounded-bl-sm border border-border/50 backdrop-blur-xl"
        )}
      >
        {isUser ? (
          <span>{text}</span>
        ) : text ? (
          <div className="prose-chat">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
          </div>
        ) : isStreaming ? (
          <span className="text-muted-foreground">
            {"Thinking"}
            <span className="loading-dots" />
          </span>
        ) : null}
      </div>
    </div>
  )
}
