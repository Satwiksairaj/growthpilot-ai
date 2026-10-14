import React from 'react'
import { Link, useLocation } from 'react-router-dom'

const NavLink = ({to, children}) => {
  const loc = useLocation()
  const active = loc.pathname === to
  return (
    <Link to={to} className={`px-3 py-2 rounded-md text-sm font-medium ${active ? 'bg-blue-600 text-white' : 'text-gray-700 hover:bg-gray-100'}`}>
      {children}
    </Link>
  )
}

export default function Header(){
  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Link to="/" className="text-xl font-semibold text-blue-600">GrowthPilot AI</Link>
            <span className="ml-3 text-sm text-gray-500">AI-powered student acquisition & growth analytics</span>
          </div>
          <nav className="flex items-center gap-2">
            <NavLink to="/">Home</NavLink>
            <NavLink to="/assessment">Assessment</NavLink>
            <NavLink to="/dashboard">Dashboard</NavLink>
          </nav>
        </div>
      </div>
    </header>
  )
}
