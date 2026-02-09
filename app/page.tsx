"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import type { UIMessage } from "ai"
import { ChatMessage } from "@/components/chat-message"
import { ChatSidebar, type ChatSession } from "@/components/chat-sidebar"
import { SettingsPanel } from "@/components/settings-panel"
import { CheckpointSidebar } from "@/components/checkpoint-sidebar"
import { ChatInput } from "@/components/chat-input"
import { Plus } from "lucide-react"

export default function Home() {
  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarView, setSidebarView] = useState<"chats" | "settings">("chats")

  // Session management (client-side only for this frontend)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState(() =>
    crypto.randomUUID()
  )

  // Model settings
  const [currentModel, setCurrentModel] = useState("llama-3.3-70b-versatile")

  // Checkpoint state
  const [checkpointedIds, setCheckpointedIds] = useState<Set<string>>(
    new Set()
  )
  const [activeMessageId, setActiveMessageId] = useState<string | null>(null)

  // Chat ref for scrolling
  const chatContainerRef = useRef<HTMLDivElement>(null)

  // Input state
  const [input, setInput] = useState("")

  // AI SDK useChat
  const { messages, sendMessage, status, setMessages, stop } = useChat({
    transport: new DefaultChatTransport({
      api: "/api/chat",
      prepareSendMessagesRequest: ({ id, messages }) => ({
        body: {
          messages,
          id,
          model: currentModel,
        },
      }),
    }),
  })

  const isLoading = status === "streaming" || status === "submitted"

  // Auto-scroll to bottom
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight
    }
  }, [messages])

  // Track scroll to highlight active message in checkpoint sidebar
  const handleScroll = useCallback(() => {
    if (!chatContainerRef.current) return
    const container = chatContainerRef.current
    const containerRect = container.getBoundingClientRect()
    const centerY = containerRect.top + containerRect.height / 2

    const messageElements = container.querySelectorAll("[data-message-id]")
    let closestId: string | null = null
    let closestDist = Infinity

    messageElements.forEach((el) => {
      const rect = el.getBoundingClientRect()
      const dist = Math.abs(rect.top + rect.height / 2 - centerY)
      if (dist < closestDist) {
        closestDist = dist
        closestId = el.getAttribute("data-message-id")
      }
    })

    setActiveMessageId(closestId)
  }, [])

  // Session management functions
  const handleNewChat = useCallback(() => {
    // Save current session if it has messages
    if (messages.length > 0) {
      const firstUserMsg = messages.find((m) => m.role === "user")
      const title = firstUserMsg
        ? getMessageText(firstUserMsg).substring(0, 30) +
          (getMessageText(firstUserMsg).length > 30 ? "..." : "")
        : "New Chat"

      setSessions((prev) => {
        const exists = prev.find((s) => s.id === currentSessionId)
        if (exists) return prev
        return [
          {
            id: currentSessionId,
            title,
            timestamp: new Date().toISOString(),
          },
          ...prev,
        ]
      })
    }

    const newId = crypto.randomUUID()
    setCurrentSessionId(newId)
    setMessages([])
    setCheckpointedIds(new Set())
    setInput("")
  }, [messages, currentSessionId, setMessages])

  const handleSend = useCallback(() => {
    if (!input.trim() || isLoading) return
    sendMessage({ text: input })
    setInput("")
  }, [input, isLoading, sendMessage])

  const handleSwitchView = useCallback(
    (view: "chats" | "settings") => {
      if (sidebarOpen && sidebarView === view) {
        setSidebarOpen(false)
      } else {
        setSidebarView(view)
        setSidebarOpen(true)
      }
    },
    [sidebarOpen, sidebarView]
  )

  const handleToggleCheckpoint = useCallback((id: string) => {
    setCheckpointedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const handleNavigateToMessage = useCallback((id: string) => {
    const el = document.querySelector(`[data-message-id="${id}"]`)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Background gradient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-[20%] w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-[20%] w-[400px] h-[400px] bg-primary/5 rounded-full blur-[100px]" />
      </div>

      {/* Sidebar */}
      <ChatSidebar
        isOpen={sidebarOpen}
        activeView={sidebarView}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onClose={() => setSidebarOpen(false)}
        onSwitchView={handleSwitchView}
        onNewChat={handleNewChat}
        onSwitchSession={(id) => {
          setCurrentSessionId(id)
          setSidebarOpen(false)
        }}
        onDeleteSession={(id) => {
          setSessions((prev) => prev.filter((s) => s.id !== id))
        }}
        settingsContent={
          <SettingsPanel
            currentModel={currentModel}
            onModelChange={setCurrentModel}
          />
        }
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col h-screen relative z-10 pr-5">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-card/30 backdrop-blur-xl">
          <h1 className="text-base font-bold tracking-tight text-foreground">
            Agentic Workspace
          </h1>
          <div className="flex items-center gap-3">
            <button
              onClick={handleNewChat}
              className="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold bg-primary text-primary-foreground hover:bg-primary/90 hover:-translate-y-px hover:shadow-lg hover:shadow-primary/40 active:translate-y-0 transition-all duration-200"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </button>
            <span className="text-xs text-muted-foreground hidden sm:inline">
              {
                (
                  [
                    { id: "llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
                    { id: "llama-3.1-8b-instant", label: "Llama 3.1 8B" },
                    { id: "mixtral-8x7b-32768", label: "Mixtral 8x7B" },
                    { id: "gemma2-9b-it", label: "Gemma 2 9B" },
                  ] as const
                ).find((m) => m.id === currentModel)?.label
              }
            </span>
          </div>
        </header>

        {/* Chat area */}
        <div
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-4"
        >
          {messages.length === 0 ? (
            <EmptyState />
          ) : (
            messages.map((message, i) => {
              const isLastAssistant =
                message.role === "assistant" &&
                i === messages.length - 1 &&
                isLoading
              return (
                <div key={message.id} data-message-id={message.id}>
                  <div className="flex items-start gap-2">
                    <ChatMessage
                      message={message}
                      isStreaming={isLastAssistant}
                    />
                    {message.role === "assistant" && (
                      <button
                        onClick={() => handleToggleCheckpoint(message.id)}
                        className={`shrink-0 mt-3 w-6 h-6 rounded flex items-center justify-center text-xs transition-all duration-200 ${
                          checkpointedIds.has(message.id)
                            ? "bg-emerald-500/20 border-emerald-500 text-emerald-500 border opacity-100"
                            : "bg-muted/30 border-border/50 text-muted-foreground border opacity-0 hover:opacity-100"
                        }`}
                        title="Checkpoint this answer"
                        style={{
                          opacity: checkpointedIds.has(message.id)
                            ? 1
                            : undefined,
                        }}
                      >
                        {"✓"}
                      </button>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Input */}
        <ChatInput
          input={input}
          onInputChange={setInput}
          onSend={handleSend}
          onStop={stop}
          isLoading={isLoading}
        />
      </div>

      {/* Checkpoint sidebar (right) */}
      <CheckpointSidebar
        messages={messages}
        checkpointedIds={checkpointedIds}
        onToggleCheckpoint={handleToggleCheckpoint}
        onNavigate={handleNavigateToMessage}
        activeMessageId={activeMessageId}
      />
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold text-foreground mb-2 text-balance">
          Agentic Workspace
        </h2>
        <p className="text-sm text-muted-foreground leading-relaxed text-pretty">
          Your professional AI assistant powered by Groq. Ask anything about
          coding, analysis, writing, or general knowledge.
        </p>
      </div>
    </div>
  )
}

function getMessageText(message: UIMessage): string {
  if (!message.parts || !Array.isArray(message.parts)) return ""
  return message.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("")
}
