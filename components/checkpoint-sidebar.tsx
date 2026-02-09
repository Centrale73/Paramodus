"use client"

import { cn } from "@/lib/utils"
import type { UIMessage } from "ai"
import { useCallback, useEffect, useRef, useState } from "react"

function getMessagePreview(message: UIMessage): string {
  if (!message.parts || !Array.isArray(message.parts)) return "Answer"
  const text = message.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("")
  if (!text) return "Answer"
  return text.length > 30 ? text.substring(0, 30) + "..." : text
}

interface CheckpointSidebarProps {
  messages: UIMessage[]
  checkpointedIds: Set<string>
  onToggleCheckpoint: (id: string) => void
  onNavigate: (id: string) => void
  activeMessageId: string | null
}

export function CheckpointSidebar({
  messages,
  checkpointedIds,
  onToggleCheckpoint,
  onNavigate,
  activeMessageId,
}: CheckpointSidebarProps) {
  const botMessages = messages.filter((m) => m.role === "assistant")

  if (botMessages.length === 0) return null

  return (
    <div className="fixed right-0 top-0 h-screen w-5 z-30 bg-card/60 border-l border-border/30 flex flex-col py-20 pb-28">
      <div className="flex-1 flex flex-col gap-1 px-1.5 overflow-hidden">
        {botMessages.map((msg) => (
          <CheckpointBlock
            key={msg.id}
            message={msg}
            isCheckpointed={checkpointedIds.has(msg.id)}
            isActive={msg.id === activeMessageId}
            onNavigate={() => onNavigate(msg.id)}
          />
        ))}
      </div>
    </div>
  )
}

function CheckpointBlock({
  message,
  isCheckpointed,
  isActive,
  onNavigate,
}: {
  message: UIMessage
  isCheckpointed: boolean
  isActive: boolean
  onNavigate: () => void
}) {
  const preview = getMessagePreview(message)

  return (
    <div
      onClick={onNavigate}
      title={preview}
      className={cn(
        "w-2 min-h-4 rounded cursor-pointer transition-all duration-200 mx-auto",
        "hover:w-3",
        isCheckpointed
          ? "w-3.5 bg-emerald-500 shadow-emerald-500/40 shadow-sm hover:w-4 hover:shadow-emerald-500/60 hover:shadow-md"
          : isActive
            ? "bg-primary/60"
            : "bg-foreground/15 hover:bg-foreground/30"
      )}
    />
  )
}
