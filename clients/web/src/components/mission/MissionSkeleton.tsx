'use client'

export function MissionSkeleton() {
  return (
    <div className="animate-pulse space-y-8">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div>
          <div className="h-4 w-32 bg-gray-300 mb-2" />
          <div className="h-6 w-48 bg-gray-300" />
        </div>
        <div className="h-16 w-28 bg-white border-2 border-gray-300" />
      </div>

      {/* Objective card skeleton */}
      <div className="card">
        <div className="flex-1">
          <div className="h-3 w-24 bg-gray-300 mb-3" />
          <div className="h-5 w-64 bg-gray-300 mb-2" />
          <div className="h-4 w-full bg-gray-300" />
        </div>
        <div className="mt-6 pt-4 border-t-2 border-gray-200">
          <div className="flex justify-between mb-2">
            <div className="h-3 w-28 bg-gray-300" />
            <div className="h-3 w-20 bg-gray-300" />
          </div>
          <div className="h-3 bg-gray-200 border-2 border-gray-300" />
        </div>
      </div>

      {/* Two column layout skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Main quests */}
        <div className="lg:col-span-3">
          <div className="h-4 w-32 bg-gray-300 mb-6 border-b-2 border-gray-300 pb-2" />
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white border-2 border-gray-300 p-4">
                <div className="flex items-center gap-4">
                  <div className="w-3 h-3 bg-gray-300 border-2 border-gray-400" />
                  <div className="flex-1">
                    <div className="h-4 w-40 bg-gray-300 mb-2" />
                    <div className="h-3 w-24 bg-gray-200" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Side quests */}
        <div className="lg:col-span-2">
          <div className="h-4 w-32 bg-gray-300 mb-6 border-b-2 border-gray-300 pb-2" />
          <div className="space-y-4">
            {[1, 2].map((i) => (
              <div key={i} className="bg-white border-2 border-gray-300 p-4">
                <div className="flex items-center gap-4">
                  <div className="w-3 h-3 bg-gray-300 border-2 border-gray-400" />
                  <div className="flex-1">
                    <div className="h-3 w-16 bg-gray-200 mb-2" />
                    <div className="h-4 w-32 bg-gray-300 mb-1" />
                    <div className="h-3 w-48 bg-gray-200" />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="card-sm mt-6">
            <div className="h-3 w-20 bg-gray-300 mb-4" />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="h-8 w-8 bg-gray-300 mb-1" />
                <div className="h-3 w-16 bg-gray-200" />
              </div>
              <div>
                <div className="h-8 w-12 bg-gray-300 mb-1" />
                <div className="h-3 w-16 bg-gray-200" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
