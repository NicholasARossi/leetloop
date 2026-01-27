'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { leetloopApi, type Submission } from '@/lib/api'
import { DifficultyBadge } from '@/components/ui/DifficultyBadge'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDistanceToNow, format } from 'date-fns'
import { clsx } from 'clsx'

const STATUSES = [
  'All',
  'Accepted',
  'Wrong Answer',
  'Time Limit Exceeded',
  'Runtime Error',
]

const DIFFICULTIES = ['All', 'Easy', 'Medium', 'Hard']

export default function SubmissionsPage() {
  const { userId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [statusFilter, setStatusFilter] = useState('All')
  const [difficultyFilter, setDifficultyFilter] = useState('All')
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null)

  useEffect(() => {
    async function loadSubmissions() {
      if (!userId) return

      setLoading(true)
      try {
        const data = await leetloopApi.getSubmissions(userId, {
          limit: 100,
          status: statusFilter === 'All' ? undefined : statusFilter,
          difficulty: difficultyFilter === 'All' ? undefined : difficultyFilter,
        })
        setSubmissions(data)
      } catch (err) {
        console.error('Failed to load submissions:', err)
      } finally {
        setLoading(false)
      }
    }

    loadSubmissions()
  }, [userId, statusFilter, difficultyFilter])

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="heading-accent text-xl">Submissions</h1>

        <div className="flex gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input py-1.5 px-3 text-sm w-auto"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <select
            value={difficultyFilter}
            onChange={(e) => setDifficultyFilter(e.target.value)}
            className="input py-1.5 px-3 text-sm w-auto"
          >
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">Loading submissions...</div>
          </div>
        ) : submissions.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-500">No submissions found.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="table-header">
              <tr>
                <th>Problem</th>
                <th>Difficulty</th>
                <th>Status</th>
                <th>Language</th>
                <th>Runtime</th>
                <th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub) => (
                <tr
                  key={sub.id}
                  className="table-row cursor-pointer"
                  onClick={() => setSelectedSubmission(sub)}
                >
                  <td>
                    <a
                      href={`https://leetcode.com/problems/${sub.problem_slug}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="font-medium text-black hover:text-coral transition-colors"
                    >
                      {sub.problem_title}
                    </a>
                  </td>
                  <td>
                    {sub.difficulty && <DifficultyBadge difficulty={sub.difficulty} />}
                  </td>
                  <td>
                    <StatusBadge status={sub.status} />
                  </td>
                  <td className="text-gray-600">
                    {sub.language || '-'}
                  </td>
                  <td className="text-gray-600">
                    {sub.runtime_ms ? `${sub.runtime_ms}ms` : '-'}
                  </td>
                  <td className="text-gray-500">
                    {formatDistanceToNow(new Date(sub.submitted_at), { addSuffix: true })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Code Modal */}
      {selectedSubmission && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedSubmission(null)}
        >
          <div
            className="card max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b-2 border-black flex justify-between items-start">
              <div>
                <h2 className="text-lg font-semibold text-black">
                  {selectedSubmission.problem_title}
                </h2>
                <div className="flex items-center gap-2 mt-2">
                  <StatusBadge status={selectedSubmission.status} />
                  {selectedSubmission.difficulty && (
                    <DifficultyBadge difficulty={selectedSubmission.difficulty} />
                  )}
                  <span className="text-sm text-gray-500">
                    {format(new Date(selectedSubmission.submitted_at), 'PPp')}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedSubmission(null)}
                className="text-gray-400 hover:text-black transition-colors"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4 overflow-auto flex-1">
              {selectedSubmission.code ? (
                <pre className="bg-gray-900 text-gray-100 p-4 border-2 border-black text-sm overflow-x-auto">
                  <code>{selectedSubmission.code}</code>
                </pre>
              ) : (
                <p className="text-gray-500">No code available for this submission.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
