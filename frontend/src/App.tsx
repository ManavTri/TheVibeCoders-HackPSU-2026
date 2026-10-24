import { Link, Route, Routes } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Landing } from './pages/Landing'
import { Report } from './pages/Report'
import { Upload } from './pages/Upload'

function Header() {
  return (
    <header className="site-header page-wrap">
      <Link to="/" className="wordmark"><span className="wordmark-icon">↗</span> clearledger<span className="wordmark-period">.</span></Link>
      <nav><Link to="/dashboard">Overview</Link><Link to="/upload" className="nav-cta">Check documents <span>↗</span></Link></nav>
    </header>
  )
}

export default function App() {
  return <><Header /><Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/upload" element={<Upload />} />
    <Route path="/report/:id" element={<Report />} />
    <Route path="*" element={<Landing />} />
  </Routes></>
}
