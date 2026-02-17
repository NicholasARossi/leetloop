import { Sidebar } from '@/components/layout/Sidebar'
import { MegaviewTabs } from '@/components/layout/MegaviewTabs'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen">
      <MegaviewTabs />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
