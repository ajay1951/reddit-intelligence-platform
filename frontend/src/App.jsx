import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import RagChat from './pages/RagChat';
import Admin from './pages/Admin';
import DeepResearch from './pages/DeepResearch';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="chat" element={<RagChat />} />
          <Route path="admin" element={<Admin />} />
          <Route path="deep-research" element={<DeepResearch />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
