'use client'

export function MissionSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div>
          <div className="h-4 w-32 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
          <div className="h-7 w-48 bg-slate-200 dark:bg-slate-700 rounded" />
        </div>
        <div className="h-10 w-28 bg-slate-200 dark:bg-slate-700 rounded-lg" />
      </div>

      {/* Objective card skeleton */}
      <div className="bg-slate-100 dark:bg-slate-800/50 rounded-2xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-slate-200 dark:bg-slate-700 rounded-xl" />
          <div className="flex-1">
            <div className="h-4 w-24 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
            <div className="h-6 w-64 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
            <div className="h-4 w-full bg-slate-200 dark:bg-slate-700 rounded" />
          </div>
        </div>
        <div className="mt-6">
          <div className="flex justify-between mb-2">
            <div className="h-4 w-28 bg-slate-200 dark:bg-slate-700 rounded" />
            <div className="h-4 w-28 bg-slate-200 dark:bg-slate-700 rounded" />
          </div>
          <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full" />
        </div>
      </div>

      {/* Two column layout skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Main quests */}
        <div className="lg:col-span-3">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 bg-slate-200 dark:bg-slate-700 rounded-full" />
            <div className="h-5 w-24 bg-slate-200 dark:bg-slate-700 rounded" />
            <div className="h-4 w-32 bg-slate-200 dark:bg-slate-700 rounded" />
          </div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="bg-slate-100 dark:bg-slate-800/50 rounded-xl p-4">
                <div className="flex items-center gap-4">
                  <div className="w-8 h-8 bg-slate-200 dark:bg-slate-700 rounded-lg" />
                  <div className="flex-1">
                    <div className="h-5 w-40 bg-slate-200 dark:bg-slate-700 rounded mb-1" />
                    <div className="h-4 w-24 bg-slate-200 dark:bg-slate-700 rounded" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Side quests */}
        <div className="lg:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 bg-slate-200 dark:bg-slate-700 rounded-full" />
            <div className="h-5 w-24 bg-slate-200 dark:bg-slate-700 rounded" />
          </div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-slate-100 dark:bg-slate-800/50 rounded-xl p-4">
                <div className="h-5 w-20 bg-slate-200 dark:bg-slate-700 rounded mb-3" />
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 bg-slate-200 dark:bg-slate-700 rounded" />
                  <div className="flex-1">
                    <div className="h-4 w-32 bg-slate-200 dark:bg-slate-700 rounded mb-1" />
                    <div className="h-3 w-48 bg-slate-200 dark:bg-slate-700 rounded" />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 bg-slate-100 dark:bg-slate-800/30 rounded-xl p-4">
            <div className="h-4 w-20 bg-slate-200 dark:bg-slate-700 rounded mb-3" />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="h-8 w-8 bg-slate-200 dark:bg-slate-700 rounded mb-1" />
                <div className="h-3 w-16 bg-slate-200 dark:bg-slate-700 rounded" />
              </div>
              <div>
                <div className="h-8 w-12 bg-slate-200 dark:bg-slate-700 rounded mb-1" />
                <div className="h-3 w-16 bg-slate-200 dark:bg-slate-700 rounded" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
