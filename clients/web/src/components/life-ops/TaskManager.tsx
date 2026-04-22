'use client'

import { useState } from 'react'
import { TaskForm } from './TaskForm'
import type { LifeOpsCategory, LifeOpsTask } from '@/lib/api'

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function recurrenceLabel(mask: number): string {
  if (mask === 127) return 'Daily'
  if (mask === 31) return 'Weekdays'
  if (mask === 96) return 'Weekends'
  const days: string[] = []
  for (let i = 0; i < 7; i++) {
    if (mask & (1 << i)) days.push(DAY_LABELS[i])
  }
  return days.join(', ') || 'Never'
}

interface TaskManagerProps {
  tasks: LifeOpsTask[]
  categories: LifeOpsCategory[]
  onCreateTask: (data: { category_id: string; title: string; description?: string; recurrence_days: number }) => Promise<void>
  onUpdateTask: (taskId: string, data: { category_id?: string; title?: string; description?: string; recurrence_days?: number; is_active?: boolean }) => Promise<void>
  onDeleteTask: (taskId: string) => Promise<void>
}

export function TaskManager({ tasks, categories, onCreateTask, onUpdateTask, onDeleteTask }: TaskManagerProps) {
  const [showForm, setShowForm] = useState(false)
  const [editingTask, setEditingTask] = useState<LifeOpsTask | null>(null)

  const categoriesById = Object.fromEntries(categories.map((c) => [c.id, c]))

  function startEdit(task: LifeOpsTask) {
    setEditingTask(task)
    setShowForm(true)
  }

  function startNew() {
    setEditingTask(null)
    setShowForm(true)
  }

  function cancel() {
    setShowForm(false)
    setEditingTask(null)
  }

  async function handleSubmit(data: { category_id: string; title: string; description?: string; recurrence_days: number }) {
    if (editingTask) {
      await onUpdateTask(editingTask.id, data)
    } else {
      await onCreateTask(data)
    }
    cancel()
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title !mb-0 !pb-0 !border-0">Tasks</h3>
        {!showForm && (
          <button onClick={startNew} className="text-xs text-gray-500 hover:text-black transition-colors">
            + Add Task
          </button>
        )}
      </div>

      {showForm && (
        <TaskForm
          categories={categories}
          onSubmit={handleSubmit}
          onCancel={cancel}
          initialData={
            editingTask
              ? {
                  category_id: editingTask.category_id || '',
                  title: editingTask.title,
                  description: editingTask.description || undefined,
                  recurrence_days: editingTask.recurrence_days,
                }
              : undefined
          }
        />
      )}

      {tasks.length === 0 && !showForm && (
        <p className="text-xs text-gray-400">No tasks yet. Add one above.</p>
      )}

      <div className="space-y-1">
        {tasks.map((task) => {
          const cat = task.category_id ? categoriesById[task.category_id] : null
          return (
            <div
              key={task.id}
              className={`flex items-center justify-between py-2.5 px-3 rounded-md hover:bg-gray-50 group ${
                !task.is_active ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                {cat && (
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
                )}
                <div className="min-w-0">
                  <span className="text-sm block truncate">{task.title}</span>
                  <span className="text-xs text-gray-400">{recurrenceLabel(task.recurrence_days)}</span>
                </div>
              </div>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                <button
                  onClick={() => onUpdateTask(task.id, { is_active: !task.is_active })}
                  className="text-xs text-gray-400 hover:text-gray-600 px-1"
                >
                  {task.is_active ? 'Pause' : 'Resume'}
                </button>
                <button
                  onClick={() => startEdit(task)}
                  className="text-xs text-gray-400 hover:text-gray-600 px-1"
                >
                  Edit
                </button>
                <button
                  onClick={() => onDeleteTask(task.id)}
                  className="text-xs text-red-400 hover:text-red-600 px-1"
                >
                  Delete
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
