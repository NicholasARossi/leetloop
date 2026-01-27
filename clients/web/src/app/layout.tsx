import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'
import { DailyAccent } from '@/components/DailyAccent'

export const metadata: Metadata = {
  title: 'LeetLoop - Systematic LeetCode Coach',
  description: 'Learn from your struggles. A personal learning system that captures LeetCode problem-solving behavior and uses spaced repetition to strengthen weak areas.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <DailyAccent />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
