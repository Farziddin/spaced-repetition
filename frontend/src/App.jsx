import { useState, useEffect } from 'react'
import Settings from './components/Settings'
import AddWord from './components/AddWord'
import WordList from './components/WordList'
import api from './api'

const TABS = ['Settings', 'Add Word', 'My Words']

export default function App() {
  const [activeTab, setActiveTab] = useState('Settings')
  const [telegramUser, setTelegramUser] = useState(null)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg) {
      tg.ready()
      tg.expand()
      const tgUser = tg.initDataUnsafe?.user
      if (tgUser) {
        setTelegramUser(tgUser)
        initUser(tgUser)
      } else {
        // Dev fallback: use a mock user with a reserved negative ID
        const mockUser = { id: -1, username: 'dev' }
        setTelegramUser(mockUser)
        initUser(mockUser)
      }
    } else {
      const mockUser = { id: -1, username: 'dev' }
      setTelegramUser(mockUser)
      initUser(mockUser)
    }
  }, [])

  async function initUser(tgUser) {
    try {
      const resp = await api.get('/users/me/init', {
        params: { telegram_id: tgUser.id, username: tgUser.username },
      })
      setUser(resp.data)
    } catch (err) {
      setError('Failed to load user data. Please restart the app.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto min-h-screen flex flex-col">
      {/* Tab Bar */}
      <nav className="flex border-b bg-white sticky top-0 z-10 shadow-sm">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="flex-1 p-4">
        {activeTab === 'Settings' && user && (
          <Settings user={user} onSave={setUser} />
        )}
        {activeTab === 'Add Word' && user && (
          <AddWord user={user} />
        )}
        {activeTab === 'My Words' && user && (
          <WordList user={user} />
        )}
      </main>
    </div>
  )
}
