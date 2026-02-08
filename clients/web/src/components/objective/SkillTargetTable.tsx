'use client'

interface SkillTargetTableProps {
  skills: Record<string, number>
  editable?: boolean
  onChange?: (skills: Record<string, number>) => void
}

function getStatusLabel(score: number): string {
  if (score >= 85) return 'STRONG'
  if (score >= 70) return 'GOOD'
  if (score >= 50) return 'FAIR'
  return 'WEAK'
}

function getStatusColor(score: number): string {
  if (score >= 85) return 'text-coral'
  if (score >= 70) return 'text-gray-600'
  if (score >= 50) return 'text-gray-700'
  return 'text-black'
}

export function SkillTargetTable({ skills, editable = false, onChange }: SkillTargetTableProps) {
  const entries = Object.entries(skills).sort((a, b) => b[1] - a[1])

  function handleScoreChange(domain: string, value: number) {
    if (onChange) {
      onChange({
        ...skills,
        [domain]: Math.max(0, Math.min(100, value)),
      })
    }
  }

  if (entries.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic">
        No skill targets defined
      </div>
    )
  }

  return (
    <div className="border-[2px] border-black overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-100 border-b-[2px] border-black">
            <th className="text-left px-4 py-2 font-bold">Domain</th>
            <th className="text-center px-4 py-2 font-bold w-24">Target</th>
            <th className="text-center px-4 py-2 font-bold w-24">Level</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([domain, score], idx) => (
            <tr
              key={domain}
              className={idx < entries.length - 1 ? 'border-b border-gray-200' : ''}
            >
              <td className="px-4 py-2 font-medium">{domain}</td>
              <td className="px-4 py-2 text-center">
                {editable ? (
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={score}
                    onChange={(e) => handleScoreChange(domain, parseInt(e.target.value) || 0)}
                    className="w-16 px-2 py-1 border-[2px] border-black text-center font-mono"
                  />
                ) : (
                  <span className="font-mono">{score}</span>
                )}
              </td>
              <td className={`px-4 py-2 text-center font-bold ${getStatusColor(score)}`}>
                {getStatusLabel(score)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
