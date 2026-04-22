'use client'

import { useState } from 'react'
import { RecurrencePicker } from './RecurrencePicker'
import type { LifeOpsCategory } from '@/lib/api'

interface TaskFormProps {
  categories: LifeOpsCategory[]
  onSubmit: (data: { category_id: string; title: string; description?: string; recurrence_days: number }) => Promise<void>
  onCancel: () => void
  initialData?: {
    category_id: string
    title: string
    description?: string
    recurrence_days: number
  }
}

export function TaskForm({ categories, onSubmit, onCancel, initialData }: TaskFormProps) {
  const [title, setTitle] = useState(initialData?.title || '')
  const [description, setDescription] = useState(initialData?.description || '')
  const [categoryId, setCategoryId] = useState(initialData?.category_id || (categories[0]?.id || ''))
  const [recurrenceDays, setRecurrenceDays] = useState(initialData?.recurrence_days ?? 127)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim() || !categoryId) return

    setSaving(true)
    try {
      await onSubmit({
        category_id: categoryId,
        title: title.trim(),
        description: description.trim() || undefined,
        recurrence_days: recurrenceDays,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card mb-4">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Morning workout"
            className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:outline-none focus:border-black"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Description (optional)
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g., 30 min cardio + stretching"
            className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:outline-none focus:border-black"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Category
          </label>
          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:outline-none focus:border-black"
            required
          >
            <option value="">Select category...</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Repeat on
          </label>
          <RecurrencePicker value={recurrenceDays} onChange={setRecurrenceDays} />
        </div>

        <div className="flex gap-2 pt-2">
          <button
            type="submit"
            disabled={saving || !title.trim() || !categoryId}
            className="btn-primary text-xs px-4 py-2"
          >
            <span className="relative z-10">{saving ? 'Saving...' : initialData ? 'Update' : 'Add Task'}</span>
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="text-xs px-4 py-2 border border-gray-200 rounded-md text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      </div>
    </form>
  )
}
