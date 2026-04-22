'use client'

const DAYS = [
  { label: 'Mon', bit: 1 },
  { label: 'Tue', bit: 2 },
  { label: 'Wed', bit: 4 },
  { label: 'Thu', bit: 8 },
  { label: 'Fri', bit: 16 },
  { label: 'Sat', bit: 32 },
  { label: 'Sun', bit: 64 },
]

interface RecurrencePickerProps {
  value: number
  onChange: (value: number) => void
}

export function RecurrencePicker({ value, onChange }: RecurrencePickerProps) {
  function toggleDay(bit: number) {
    onChange(value ^ bit)
  }

  function setDaily() {
    onChange(127)
  }

  function setWeekdays() {
    onChange(1 + 2 + 4 + 8 + 16) // Mon-Fri = 31
  }

  function setWeekends() {
    onChange(32 + 64) // Sat+Sun = 96
  }

  const isDaily = value === 127
  const isWeekdays = value === 31
  const isWeekends = value === 96

  return (
    <div>
      <div className="flex gap-1 mb-2">
        {DAYS.map((day) => {
          const active = (value & day.bit) !== 0
          return (
            <button
              key={day.label}
              type="button"
              onClick={() => toggleDay(day.bit)}
              className={`w-9 h-9 text-xs font-semibold rounded-md border transition-colors ${
                active
                  ? 'bg-black text-white border-black'
                  : 'bg-white text-gray-400 border-gray-200 hover:border-gray-300'
              }`}
            >
              {day.label}
            </button>
          )
        })}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={setDaily}
          className={`text-xs px-2 py-1 rounded border transition-colors ${
            isDaily ? 'bg-gray-100 border-gray-300 font-semibold' : 'border-gray-200 text-gray-400 hover:text-gray-600'
          }`}
        >
          Daily
        </button>
        <button
          type="button"
          onClick={setWeekdays}
          className={`text-xs px-2 py-1 rounded border transition-colors ${
            isWeekdays ? 'bg-gray-100 border-gray-300 font-semibold' : 'border-gray-200 text-gray-400 hover:text-gray-600'
          }`}
        >
          Weekdays
        </button>
        <button
          type="button"
          onClick={setWeekends}
          className={`text-xs px-2 py-1 rounded border transition-colors ${
            isWeekends ? 'bg-gray-100 border-gray-300 font-semibold' : 'border-gray-200 text-gray-400 hover:text-gray-600'
          }`}
        >
          Weekends
        </button>
      </div>
    </div>
  )
}
