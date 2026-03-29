'use client'

import { useParams } from 'next/navigation'
import { QuestionList } from '@/components/onsite-prep'

export default function CategoryPage() {
  const params = useParams()
  const category = params.category as string

  return <QuestionList category={category} />
}
