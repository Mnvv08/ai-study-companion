import React, { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

/**
 * AppNavbar
 * Props:
 *   currentView  — 'workspace' | 'analytics' | 'settings'
 *   onViewChange — (view: string) => void
 *   personaMode  — bool   (shows a badge when Hinglish Mentor is active)
 */
export default function AppNavbar({ currentView, onViewChange, personaMode = false }) {
  const { user, logout } = useContext(AuthContext);

  const tabs = [
    { id: 'workspace', label: 'Workspace', icon: '📚' },
    { id: 'analytics', label: 'My Progress', icon: '📊' },
    { id: 'settings',  label: 'Settings',    icon: '⚙️'  },
  ];

  return (
    <nav className="bg-white border-b border-gray-200 flex-shrink-0 sticky top-0 z-30">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">

          {/* Brand */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-2xl select-none">🎓</span>
            <span className="text-base sm:text-lg font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent leading-none">
              AI Study Companion
            </span>
          </div>

          {/* Desktop nav tabs */}
          <div className="hidden sm:flex items-center gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => onViewChange(tab.id)}
                className={`nav-tab ${
                  currentView === tab.id ? 'nav-tab-active' : 'nav-tab-inactive'
                }`}
              >
                <span className="mr-1.5">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Right section: persona badge + user + logout */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {personaMode && (
              <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-orange-100 text-orange-700 text-xs font-bold border border-orange-200">
                🇮🇳 Hinglish ON
              </span>
            )}
            <span className="hidden md:block text-sm text-gray-600">
              Hi, <strong className="text-gray-900">{user?.name || 'Student'}</strong>
            </span>
            <button onClick={logout} className="btn-secondary text-xs py-1.5 px-3">
              Sign out
            </button>
          </div>
        </div>

        {/* Mobile nav tabs row */}
        <div className="flex sm:hidden gap-1 pb-2 -mt-1 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onViewChange(tab.id)}
              className={`nav-tab flex-shrink-0 text-xs ${
                currentView === tab.id ? 'nav-tab-active' : 'nav-tab-inactive'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
          {personaMode && (
            <span className="flex-shrink-0 inline-flex items-center px-2 py-1 rounded-full bg-orange-100 text-orange-700 text-xs font-bold border border-orange-200">
              🇮🇳
            </span>
          )}
        </div>
      </div>
    </nav>
  );
}
