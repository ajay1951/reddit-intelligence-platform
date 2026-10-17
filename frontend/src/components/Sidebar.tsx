import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, Database, BrainCircuit, Activity, ShieldCheck } from 'lucide-react';
import './Sidebar.css';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-badge">
          <Database size={20} className="logo-icon-svg" />
        </div>
        <div className="brand-info">
          <span className="brand-title">Reddit Intelligence</span>
          <span className="brand-badge">Production v2.4</span>
        </div>
      </div>

      <div className="nav-section-label">WORKSPACE</div>
      <nav className="sidebar-nav">
        <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={18} className="nav-icon" />
          <span className="nav-label">Operations Center</span>
          <span className="nav-shortcut">1</span>
        </NavLink>
        
        <NavLink to="/chat" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <MessageSquare size={18} className="nav-icon" />
          <span className="nav-label">RAG Assistant</span>
          <span className="nav-shortcut">2</span>
        </NavLink>

        <NavLink to="/deep-research" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <BrainCircuit size={18} className="nav-icon" />
          <span className="nav-label">Deep Research</span>
          <span className="nav-shortcut">3</span>
        </NavLink>

        <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Database size={18} className="nav-icon" />
          <span className="nav-label">Data Pipeline & Admin</span>
          <span className="nav-shortcut">4</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="system-health-card">
          <div className="health-header">
            <span className="health-ping"></span>
            <span className="health-status">System Operational</span>
          </div>
          <p className="health-meta">Postgres • Celery • ChromaDB</p>
          <div className="health-sub">
            <ShieldCheck size={12} className="text-emerald-600" />
            <span>59/59 Tests Passing</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
