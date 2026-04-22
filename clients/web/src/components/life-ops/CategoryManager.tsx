'use client'

import { useState } from 'react'
import type { LifeOpsCategory } from '@/lib/api'

const COLOR_OPTIONS = [
  '#6B7280', '#EF4444', '#F97316', '#EAB308', '#22C55E',
  '#06B6D4', '#3B82F6', '#8B5CF6', '#EC4899',
]

interface CategoryManagerProps {
  categories: LifeOpsCategory[]
  onCreateCategory: (name: string, color: string) => Promise<void>
  onUpdateCategory: (id: string, name: string, color: string) => Promise<void>
  onDeleteCategory: (id: string) => Promise<void>
}

export function CategoryManager({
  categories,
  onCreateCategory,
  onUpdateCategory,
  onDeleteCategory,
}: CategoryManagerProps) {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [color, setColor] = useState(COLOR_OPTIONS[0])
  const [saving, setSaving] = useState(false)

  function startEdit(cat: LifeOpsCategory) {
    setEditingId(cat.id)
    setName(cat.name)
    setColor(cat.color)
    setShowForm(true)
  }

  function startNew() {
    setEditingId(null)
    setName('')
    setColor(COLOR_OPTIONS[0])
    setShowForm(true)
  }

  function cancel() {
    setShowForm(false)
    setEditingId(null)
    setName('')
    setColor(COLOR_OPTIONS[0])
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return

    setSaving(true)
    try {
      if (editingId) {
        await onUpdateCategory(editingId, name.trim(), color)
      } else {
        await onCreateCategory(name.trim(), color)
      }
      cancel()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title !mb-0 !pb-0 !border-0">Categories</h3>
        {!showForm && (
          <button onClick={startNew} className="text-xs text-gray-500 hover:text-black transition-colors">
            + Add Category
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-4 p-3 bg-gray-50 rounded-md">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Category name"
            className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus:outline-none focus:border-black mb-2"
            required
            autoFocus
          />
          <div className="flex gap-1.5 mb-3">
            {COLOR_OPTIONS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className={`w-6 h-6 rounded-full border-2 transition-all ${
                  color === c ? 'border-black scale-110' : 'border-transparent hover:scale-105'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="btn-primary text-xs px-3 py-1.5"
            >
              <span className="relative z-10">{saving ? 'Saving...' : editingId ? 'Update' : 'Add'}</span>
            </button>
            <button
              type="button"
              onClick={cancel}
              className="text-xs px-3 py-1.5 text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {categories.length === 0 && !showForm && (
        <p className="text-xs text-gray-400">No categories yet. Create one to get started.</p>
      )}

      <div className="space-y-1">
        {categories.map((cat) => (
          <div key={cat.id} className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-gray-50 group">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
              <span className="text-sm">{cat.name}</span>
            </div>
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => startEdit(cat)}
                className="text-xs text-gray-400 hover:text-gray-600 px-1"
              >
                Edit
              </button>
              <button
                onClick={() => onDeleteCategory(cat.id)}
                className="text-xs text-red-400 hover:text-red-600 px-1"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
