import { useState } from 'react'
import api from '../api'

const LANGUAGES = [
  'English', 'Spanish', 'French', 'German', 'Italian',
  'Portuguese', 'Russian', 'Chinese', 'Japanese', 'Korean',
  'Arabic', 'Turkish', 'Polish', 'Dutch', 'Swedish',
]

export default function Settings({ user, onSave }) {
  const [form, setForm] = useState({
    target_language: user.target_language || 'English',
    native_language: user.native_language || 'Uzbek',
    daily_limit: user.daily_limit || 10,
    review_time: user.review_time
      ? user.review_time.substring(0, 5)
      : '20:00',
  })
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const payload = {
        target_language: form.target_language,
        native_language: form.native_language,
        daily_limit: parseInt(form.daily_limit, 10),
        review_time: form.review_time + ':00',
      }
      const resp = await api.patch(`/users/${user.telegram_id}`, payload)
      onSave(resp.data)
      setMessage({ type: 'success', text: '✅ Settings saved!' })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Save failed. Please try again.'
      setMessage({ type: 'error', text: detail })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">⚙️ Settings</h1>

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

      <form onSubmit={handleSave} className="space-y-4">
        {/* Target Language */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Target Language (language you are learning)
          </label>
          <select
            value={form.target_language}
            onChange={(e) => setForm({ ...form, target_language: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>

        {/* Native Language */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Native Language
          </label>
          <select
            value={form.native_language}
            onChange={(e) => setForm({ ...form, native_language: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {LANGUAGES.concat(['Uzbek']).sort().map((lang) => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>

        {/* Daily Limit */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Daily New Words Limit: <span className="font-bold text-blue-600">{form.daily_limit}</span>
          </label>
          <input
            type="range"
            min="1"
            max="50"
            value={form.daily_limit}
            onChange={(e) => setForm({ ...form, daily_limit: e.target.value })}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>1</span>
            <span>25</span>
            <span>50</span>
          </div>
        </div>

        {/* Review Time */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Daily Review Time
          </label>
          <input
            type="time"
            value={form.review_time}
            onChange={(e) => setForm({ ...form, review_time: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  )
}
