import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Home } from './pages/Home';
import { OAuthCallback } from './pages/OAuthCallback';
import { Dashboard } from './pages/Dashboard';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[var(--color-destiny-dark)] text-white selection:bg-[var(--color-destiny-accent)] selection:text-slate-900 font-sans">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/auth/callback" element={<OAuthCallback />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;