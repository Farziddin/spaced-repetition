import { useState } from 'react'
import api from '../api'

export default function AddWord({ user }) {
  const [word, setWord] = useState('')
  const [variants, setVariants] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [step, setStep] = useState('input') // 'input' | 'select'

  async function handleLookup(e) {
    e.preventDefault()
    if (!word.trim()) return
    setLoading(true)
    setMessage(null)
    setVariants([])
    try {
      const resp = await api.post('/words/lookup', {
        word: word.trim(),
        target_language: user.target_language,
        native_language: user.native_language,
      })
      setVariants(resp.data.variants)
      setStep('select')
    } catch (err) {
      const detail = err.response?.data?.detail || 'Could not fetch translations. Please try again.'
      setMessage({ type: 'error', text: detail })
    } finally {
      setLoading(false)
    }
  }

  async function handleSelect(variant) {
    setSaving(true)
    setMessage(null)
    try {
      await api.post(`/words/add?telegram_id=${user.telegram_id}`, {
        word: word.trim(),
        target_language: user.target_language,
        context: variant.context,
        native_translation: variant.translation,
      })
      setMessage({ type: 'success', text: `✅ "${word}" (${variant.context}) added to your word list!` })
      setWord('')
      setVariants([])
      setStep('input')
    } catch (err) {
      const detail = err.response?.data?.detail || 'Could not save word. Please try again.'
      setMessage({ type: 'error', text: detail })
    } finally {
      setSaving(false)
    }
  }

  function handleBack() {
    setStep('input')
    setVariants([])
    setMessage(null)
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">➕ Add New Word</h1>

      {message && (
        <div
          className={`mb-4 px-4 py-3 rounded text-sm ${
            message.type === 'success'
              ? 'bg-green-100 border border-green-400 text-green-700'
              : 'bg-red-100 border border-red-400 text-red-700'
          }`}
        >
          {message.text}
        </div>
      )}

      {step === 'input' && (
        <form onSubmit={handleLookup} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Enter a word in <span className="font-bold text-blue-600">{user.target_language}</span>
            </label>
            <input
              type="text"
              value={word}
              onChange={(e) => setWord(e.target.value)}
              placeholder={`e.g. right`}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !word.trim()}
            className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
          >
            {loading ? 'Looking up...' : 'Look Up Translations'}
          </button>
        </form>
      )}

      {step === 'select' && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={handleBack}
              className="text-sm text-blue-500 hover:text-blue-700"
            >
              ← Back
            </button>
            <h2 className="text-base font-semibold">
              Select the meaning of "<span className="text-blue-600">{word}</span>"
            </h2>
          </div>
          <p className="text-xs text-gray-500 mb-3">
            Choose the specific context/translation you want to learn:
          </p>
          <div className="space-y-2">
            {variants.map((v, i) => (
              <button
                key={i}
                onClick={() => handleSelect(v)}
                disabled={saving}
                className="w-full text-left border border-gray-200 rounded-lg p-3 hover:bg-blue-50 hover:border-blue-300 transition-colors disabled:opacity-50"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-sm font-medium text-gray-800">{v.translation}</span>
                    <span className="ml-2 text-xs text-blue-500 bg-blue-50 px-2 py-0.5 rounded-full">
                      {v.context}
                    </span>
                  </div>
                </div>
                {v.example && (
                  <p className="text-xs text-gray-500 mt-1 italic">"{v.example}"</p>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
