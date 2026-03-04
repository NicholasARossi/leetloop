import { Sidebar } from '@/components/layout/Sidebar'
import { MegaviewTabs } from '@/components/layout/MegaviewTabs'
import { MainContent } from '@/components/layout/MainContent'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen">
      <MegaviewTabs />
      <div className="flex flex-1">
        <Sidebar />
        <MainContent>
          {children}
        </MainContent>
      </div>
    </div>
  )
}
