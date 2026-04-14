import { useState, useEffect } from 'react'
import api from '../api'

export default function WordList({ user }) {
  const [words, setWords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchWords()
  }, [user.telegram_id])

  async function fetchWords() {
    setLoading(true)
    try {
      const resp = await api.get('/words/', {
        params: { telegram_id: user.telegram_id },
      })
      setWords(resp.data)
    } catch (err) {
      setError('Could not load your words.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded text-sm">
        {error}
      </div>
    )
  }

  if (words.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-4xl mb-3">📚</p>
        <p className="text-base font-medium">No words yet!</p>
        <p className="text-sm">Go to "Add Word" to start building your vocabulary.</p>
      </div>
    )
  }

  const now = new Date()

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">📚 My Words</h1>
        <span className="text-sm text-gray-500">{words.length} words</span>
      </div>
      <div className="space-y-2">
        {words.map((w) => {
          const nextReview = new Date(w.next_review)
          const isDue = nextReview <= now
          return (
            <div
              key={w.id}
              className="border border-gray-200 rounded-lg p-3 bg-white shadow-sm"
            >
              <div className="flex justify-between items-start">
                <div>
                  <span className="font-semibold text-gray-800">{w.word}</span>
                  <span className="ml-2 text-xs text-blue-500 bg-blue-50 px-2 py-0.5 rounded-full">
                    {w.context}
                  </span>
                </div>
                {isDue && (
                  <span className="text-xs text-orange-500 bg-orange-50 px-2 py-0.5 rounded-full font-medium">
                    Due
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 mt-1">{w.native_translation}</p>
              <div className="flex gap-3 mt-2 text-xs text-gray-400">
                <span>Reps: {w.repetition_count}</span>
                <span>Interval: {w.srs_interval}d</span>
                <span>Next: {nextReview.toLocaleDateString()}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
