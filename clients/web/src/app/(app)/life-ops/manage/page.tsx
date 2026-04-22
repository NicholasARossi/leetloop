'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  leetloopApi,
  type LifeOpsCategory,
  type LifeOpsTask,
} from '@/lib/api'
import { CategoryManager, TaskManager } from '@/components/life-ops'

export default function ManageTasksPage() {
  const { userId } = useAuth()

  const [loading, setLoading] = useState(true)
  const [categories, setCategories] = useState<LifeOpsCategory[]>([])
  const [tasks, setTasks] = useState<LifeOpsTask[]>([])

  const loadData = useCallback(async () => {
    if (!userId) return
    setLoading(true)
    try {
      const [cats, tsks] = await Promise.all([
        leetloopApi.getLifeOpsCategories(userId),
        leetloopApi.getLifeOpsTasks(userId),
      ])
      setCategories(cats)
      setTasks(tsks)
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleCreateCategory(name: string, color: string) {
    if (!userId) return
    const cat = await leetloopApi.createLifeOpsCategory(userId, { name, color })
    setCategories((prev) => [...prev, cat])
  }

  async function handleUpdateCategory(id: string, name: string, color: string) {
    const cat = await leetloopApi.updateLifeOpsCategory(id, { name, color })
    setCategories((prev) => prev.map((c) => (c.id === id ? cat : c)))
  }

  async function handleDeleteCategory(id: string) {
    await leetloopApi.deleteLifeOpsCategory(id)
    setCategories((prev) => prev.filter((c) => c.id !== id))
    // Also remove tasks in this category from local state
    setTasks((prev) => prev.filter((t) => t.category_id !== id))
  }

  async function handleCreateTask(data: { category_id: string; title: string; description?: string; recurrence_days: number }) {
    if (!userId) return
    const task = await leetloopApi.createLifeOpsTask(userId, data)
    setTasks((prev) => [...prev, task])
  }

  async function handleUpdateTask(taskId: string, data: { category_id?: string; title?: string; description?: string; recurrence_days?: number; is_active?: boolean }) {
    const task = await leetloopApi.updateLifeOpsTask(taskId, data)
    setTasks((prev) => prev.map((t) => (t.id === taskId ? task : t)))
  }

  async function handleDeleteTask(taskId: string) {
    await leetloopApi.deleteLifeOpsTask(taskId)
    setTasks((prev) => prev.filter((t) => t.id !== taskId))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500 text-sm">Loading...</p>
      </div>
    )
  }

  return (
    <div className="animate-fadeIn">
      <CategoryManager
        categories={categories}
        onCreateCategory={handleCreateCategory}
        onUpdateCategory={handleUpdateCategory}
        onDeleteCategory={handleDeleteCategory}
      />
      <TaskManager
        tasks={tasks}
        categories={categories}
        onCreateTask={handleCreateTask}
        onUpdateTask={handleUpdateTask}
        onDeleteTask={handleDeleteTask}
      />
    </div>
  )
}
