import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, Database, BrainCircuit } from 'lucide-react';
import './Sidebar.css';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-icon">
          <Database size={24} color="#fff" />
        </div>
        <h2 className="gradient-text">Intelligence</h2>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={20} />
          <span>Dashboard</span>
        </NavLink>
        
        <NavLink to="/chat" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <MessageSquare size={20} />
          <span>AI Chat</span>
        </NavLink>

        <NavLink to="/deep-research" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <BrainCircuit size={20} />
          <span>Deep Research</span>
        </NavLink>

        <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Database size={20} />
          <span>Admin</span>
        </NavLink>
      </nav>
    </aside>
  );
}
