"use client"

import { cn } from "@/lib/utils"
import {
  MessageSquare,
  Settings,
  X,
  Plus,
  Trash2,
} from "lucide-react"
import { useState } from "react"

export interface ChatSession {
  id: string
  title: string
  timestamp: string
}

interface ChatSidebarProps {
  isOpen: boolean
  activeView: "chats" | "settings"
  sessions: ChatSession[]
  currentSessionId: string
  onClose: () => void
  onSwitchView: (view: "chats" | "settings") => void
  onNewChat: () => void
  onSwitchSession: (id: string) => void
  onDeleteSession: (id: string) => void
  settingsContent: React.ReactNode
}

export function ChatSidebar({
  isOpen,
  activeView,
  sessions,
  currentSessionId,
  onClose,
  onSwitchView,
  onNewChat,
  onSwitchSession,
  onDeleteSession,
  settingsContent,
}: ChatSidebarProps) {
  return (
    <>
      {/* Sidebar */}
      <div
        className={cn(
          "fixed left-0 top-0 h-screen w-80 z-50 border-r border-border/50",
          "bg-card/95 backdrop-blur-xl shadow-2xl shadow-black/30",
          "transition-transform duration-300 ease-out",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 pb-4 border-b border-border/50">
          <h3 className="text-sm font-semibold tracking-tight text-foreground">
            {activeView === "chats" ? "Chats" : "Settings"}
          </h3>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="h-[calc(100%-64px)] overflow-y-auto p-4">
          {activeView === "chats" ? (
            <div className="flex flex-col gap-2">
              <button
                onClick={onNewChat}
                className="flex items-center gap-2 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-primary-foreground bg-primary hover:bg-primary/90 transition-colors"
              >
                <Plus className="h-4 w-4" />
                New Chat
              </button>

              <div className="mt-2 flex flex-col gap-1">
                {sessions.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4 italic">
                    No previous chats
                  </p>
                ) : (
                  sessions.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      isActive={session.id === currentSessionId}
                      onSelect={() => onSwitchSession(session.id)}
                      onDelete={() => onDeleteSession(session.id)}
                    />
                  ))
                )}
              </div>
            </div>
          ) : (
            settingsContent
          )}
        </div>
      </div>

      {/* Toggle tabs */}
      <div
        className={cn(
          "fixed top-6 z-[51] flex flex-col gap-2 transition-all duration-300 ease-out",
          isOpen ? "left-80" : "left-0"
        )}
      >
        <button
          onClick={() => onSwitchView("chats")}
          className={cn(
            "flex items-center justify-center w-12 h-12",
            "rounded-r-xl border border-l-0 border-border/50",
            "shadow-lg shadow-black/20 transition-all duration-200",
            activeView === "chats" && isOpen
              ? "bg-primary text-primary-foreground"
              : "bg-card text-foreground hover:translate-x-0.5"
          )}
          title="Chats"
        >
          <MessageSquare className="h-5 w-5" />
        </button>
        <button
          onClick={() => onSwitchView("settings")}
          className={cn(
            "flex items-center justify-center w-12 h-12",
            "rounded-r-xl border border-l-0 border-border/50",
            "shadow-lg shadow-black/20 transition-all duration-200",
            activeView === "settings" && isOpen
              ? "bg-primary text-primary-foreground"
              : "bg-card text-foreground hover:translate-x-0.5"
          )}
          title="Settings"
        >
          <Settings className="h-5 w-5" />
        </button>
      </div>

      {/* Overlay when open */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}
    </>
  )
}

function SessionItem({
  session,
  isActive,
  onSelect,
  onDelete,
}: {
  session: ChatSession
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const [showDelete, setShowDelete] = useState(false)

  return (
    <div
      className={cn(
        "flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer",
        "transition-all duration-200 group",
        isActive
          ? "bg-primary/15 border border-primary/30"
          : "hover:bg-muted/50 border border-transparent"
      )}
      onClick={onSelect}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate text-foreground">
          {session.title}
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {new Date(session.timestamp).toLocaleDateString()}
        </p>
      </div>
      {showDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
          className="p-1 rounded text-muted-foreground hover:text-destructive transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}
