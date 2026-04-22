'use client'

import { useState } from 'react'
import type { MistakeJournalEntry } from '@/lib/api'

interface MistakeJournalCardProps {
  entries: MistakeJournalEntry[]
  unaddressedCount: number
  onAdd: (text: string) => Promise<void>
  onDelete: (entryId: string) => Promise<void>
}

export function MistakeJournalCard({ entries, unaddressedCount, onAdd, onDelete }: MistakeJournalCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [draft, setDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!draft.trim() || submitting) return
    setSubmitting(true)
    try {
      await onAdd(draft.trim())
      setDraft('')
    } finally {
      setSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleDelete = async (entryId: string) => {
    setDeletingId(entryId)
    try {
      await onDelete(entryId)
    } finally {
      setDeletingId(null)
    }
  }

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="card-sm w-full text-left flex items-center gap-2 group hover:border-accent transition-colors"
      >
        <svg className="w-3.5 h-3.5 text-gray-400 group-hover:text-accent flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
        <span className="text-xs text-gray-500 group-hover:text-accent truncate">
          {unaddressedCount > 0
            ? `${unaddressedCount} mistake${unaddressedCount === 1 ? '' : 's'} logged`
            : 'Log a mistake or insight...'}
        </span>
      </button>
    )
  }

  return (
    <div className="card-sm space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wide text-gray-500">Mistake Journal</span>
        <button onClick={() => setExpanded(false)} className="text-xs text-gray-400 hover:text-black">
          Collapse
        </button>
      </div>

      {/* Existing entries */}
      {entries.length > 0 && (
        <div className="max-h-40 overflow-y-auto space-y-1.5">
          {entries.map((entry) => (
            <div key={entry.id} className="flex items-start gap-2 text-xs group/entry">
              <span className="text-gray-600 flex-1 min-w-0">
                {entry.entry_text}
                {entry.tags.length > 0 && (
                  <span className="ml-1.5 inline-flex gap-1">
                    {entry.tags.slice(0, 2).map((tag) => (
                      <span key={tag} className="tag text-[9px]">{tag}</span>
                    ))}
                  </span>
                )}
              </span>
              <button
                onClick={() => handleDelete(entry.id)}
                disabled={deletingId === entry.id}
                className="text-gray-300 hover:text-coral flex-shrink-0 opacity-0 group-hover/entry:opacity-100 transition-opacity"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value.slice(0, 1000))}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Off by one in binary search again..."
          className="flex-1 border border-gray-200 rounded px-2 py-1.5 text-xs text-black placeholder:text-gray-400 focus:outline-none focus:border-accent"
          disabled={submitting}
          autoFocus
        />
        <button
          onClick={handleSubmit}
          disabled={!draft.trim() || submitting}
          className="btn-primary text-xs flex-shrink-0"
        >
          {submitting ? '...' : 'Add'}
        </button>
      </div>
    </div>
  )
}
