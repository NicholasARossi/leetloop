'use client'

import { useState } from 'react'

interface FocusNotesCardProps {
  focusNotes: string | null
  onSave: (notes: string | null) => Promise<void>
}

const MAX_LENGTH = 500

export function FocusNotesCard({ focusNotes, onSave }: FocusNotesCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [draft, setDraft] = useState(focusNotes ?? '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      const value = draft.trim() || null
      await onSave(value)
      setExpanded(false)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setDraft(focusNotes ?? '')
    setExpanded(false)
  }

  const handleExpand = () => {
    setDraft(focusNotes ?? '')
    setExpanded(true)
  }

  if (!expanded) {
    return (
      <button
        onClick={handleExpand}
        className="card-sm w-full text-left flex items-center gap-2 group hover:border-accent transition-colors"
      >
        <svg className="w-3.5 h-3.5 text-gray-400 group-hover:text-accent flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
        </svg>
        <span className="text-xs text-gray-500 group-hover:text-accent truncate">
          {focusNotes || 'Set focus notes to steer your feed...'}
        </span>
      </button>
    )
  }

  return (
    <div className="card-sm space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wide text-gray-500">Focus Notes</span>
        <span className="text-[10px] text-gray-400 font-mono">{draft.length}/{MAX_LENGTH}</span>
      </div>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value.slice(0, MAX_LENGTH))}
        placeholder='e.g. "Focus on graph problems this week" or "More sliding window practice"'
        className="w-full border border-gray-200 rounded px-2 py-1.5 text-xs text-black placeholder:text-gray-400 focus:outline-none focus:border-accent resize-none"
        rows={3}
        autoFocus
      />
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={handleCancel}
          className="text-xs text-gray-500 hover:text-black px-2 py-1"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary text-xs"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  )
}
