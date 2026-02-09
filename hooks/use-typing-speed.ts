"use client"

import { useState, useRef, useCallback } from "react"

export type TypingMood = "slow" | "neutral" | "fast"

const SAMPLE_SIZE = 10
const SLOW_THRESHOLD_MS = 400
const FAST_THRESHOLD_MS = 150

export function useTypingSpeed() {
  const [mood, setMood] = useState<TypingMood>("neutral")
  const [avgInterval, setAvgInterval] = useState<number>(0)
  const lastKeyTime = useRef(0)
  const intervals = useRef<number[]>([])

  const handleKeystroke = useCallback(() => {
    const now = Date.now()
    if (lastKeyTime.current > 0) {
      const interval = now - lastKeyTime.current
      intervals.current.push(interval)

      // Keep only the last N samples
      if (intervals.current.length > SAMPLE_SIZE) {
        intervals.current.shift()
      }

      // Need at least 5 samples for a reliable average
      if (intervals.current.length >= 5) {
        const avg =
          intervals.current.reduce((a, b) => a + b, 0) /
          intervals.current.length
        setAvgInterval(avg)

        if (avg > SLOW_THRESHOLD_MS) {
          setMood("slow")
        } else if (avg < FAST_THRESHOLD_MS) {
          setMood("fast")
        } else {
          setMood("neutral")
        }
      }
    }
    lastKeyTime.current = now
  }, [])

  const reset = useCallback(() => {
    intervals.current = []
    lastKeyTime.current = 0
    setMood("neutral")
    setAvgInterval(0)
  }, [])

  return { mood, avgInterval, handleKeystroke, reset }
}
