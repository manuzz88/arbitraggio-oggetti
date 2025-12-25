import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Items from './pages/Items'
import Opportunities from './pages/Opportunities'
import Listings from './pages/Listings'
import Orders from './pages/Orders'
import Settings from './pages/Settings'
import TelegramApp from './telegram-app/TelegramApp'

function App() {
  return (
    <Routes>
      {/* Telegram Mini App - standalone senza layout */}
      <Route path="/tg" element={<TelegramApp />} />
      
      {/* Web App normale */}
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="items" element={<Items />} />
        <Route path="opportunities" element={<Opportunities />} />
        <Route path="listings" element={<Listings />} />
        <Route path="orders" element={<Orders />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default App
