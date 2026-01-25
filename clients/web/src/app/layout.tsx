import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'

const inter = Inter({ subsets: ['latin'] })

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
      <body className={`${inter.className} bg-slate-50 dark:bg-slate-900`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
