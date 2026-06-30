import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Analytics } from '@vercel/analytics/react'
import NavBar from './components/NavBar'
import GoalToasts from './components/GoalToasts'
import Dashboard from './pages/Dashboard'
import Groups from './pages/Groups'
import Knockout from './pages/Knockout'
import Awards from './pages/Awards'
import Match from './pages/Match'
import Matches from './pages/Matches'
import Bracket from './pages/Bracket'
import About from './pages/About'
import Path from './pages/Path'
import Scenario from './pages/Scenario'
import FinalMatchups from './pages/FinalMatchups'
import Road from './pages/Road'
import Movers from './pages/Movers'

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <main style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px' }}>
        <Routes>
          <Route path="/"           element={<Dashboard />} />
          <Route path="/groups"     element={<Groups />} />
          <Route path="/knockout"   element={<Knockout />} />
          <Route path="/awards"     element={<Awards />} />
          <Route path="/matches"    element={<Matches />} />
          <Route path="/bracket"    element={<Bracket />} />
          <Route path="/final"      element={<FinalMatchups />} />
          <Route path="/road"       element={<Road />} />
          <Route path="/movers"     element={<Movers />} />
          <Route path="/match/:id"  element={<Match />} />
          <Route path="/about"      element={<About />} />
          <Route path="/path"       element={<Path />} />
          <Route path="/scenario"   element={<Scenario />} />
        </Routes>
      </main>
      <GoalToasts />
      <Analytics />
    </BrowserRouter>
  )
}
