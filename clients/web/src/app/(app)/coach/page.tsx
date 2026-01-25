'use client'

import { useEffect, useRef, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type ChatMessage } from '@/lib/api'
import { clsx } from 'clsx'

export default function CoachPage() {
  const { userId } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [tips, setTips] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Load personalized tips on mount
    async function loadTips() {
      if (!userId) return
      try {
        const data = await leetloopApi.getTips(userId)
        setTips(data.tips)
      } catch (err) {
        console.error('Failed to load tips:', err)
      }
    }
    loadTips()
  }, [userId])

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    if (!input.trim() || !userId || loading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await leetloopApi.chat(
        userId,
        userMessage.content,
        undefined,
        messages
      )

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.message,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      console.error('Chat error:', err)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const quickPrompts = [
    'What should I practice next?',
    'Explain two pointers technique',
    'How do I approach DP problems?',
    'Review my weak areas',
  ]

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          AI Coach
        </h1>
      </div>

      <div className="flex-1 flex gap-6 min-h-0">
        {/* Chat Area */}
        <div className="flex-1 card flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                  Welcome to your AI Coach
                </h2>
                <p className="text-slate-500 mb-6">
                  Ask questions about algorithms, get help with problems, or review your progress.
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {quickPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => setInput(prompt)}
                      className="px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 rounded-lg text-slate-700 dark:text-slate-300 transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={clsx(
                    'flex',
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  <div
                    className={clsx(
                      'max-w-[80%] px-4 py-2 rounded-lg',
                      msg.role === 'user'
                        ? 'bg-brand-600 text-white'
                        : 'bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white'
                    )}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 dark:bg-slate-700 px-4 py-2 rounded-lg">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-slate-200 dark:border-slate-700 p-4">
            <div className="flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about algorithms, problems, or your progress..."
                className="input resize-none"
                rows={2}
                disabled={loading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className={clsx(
                  'btn-primary px-6',
                  (!input.trim() || loading) && 'opacity-50 cursor-not-allowed'
                )}
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Tips Sidebar */}
        <div className="w-80 card p-4 hidden lg:block">
          <h2 className="font-semibold text-slate-900 dark:text-white mb-4">
            Personalized Tips
          </h2>
          {tips.length === 0 ? (
            <p className="text-sm text-slate-500">
              Tips will appear here based on your practice patterns.
            </p>
          ) : (
            <ul className="space-y-3">
              {tips.map((tip, idx) => (
                <li
                  key={idx}
                  className="text-sm text-slate-600 dark:text-slate-400 pl-4 border-l-2 border-brand-500"
                >
                  {tip}
                </li>
              ))}
            </ul>
          )}

          <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
            <h3 className="font-medium text-slate-900 dark:text-white mb-2">
              Quick Questions
            </h3>
            <div className="space-y-2">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setInput(prompt)}
                  className="w-full text-left text-sm text-slate-600 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
