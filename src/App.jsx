import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Assessment from './pages/Assessment'
import Dashboard from './pages/Dashboard'
import Header from './components/Header'
import VisitTracker from './components/VisitTracker'

export default function App(){
  return (
    <div className="min-h-screen flex flex-col">
      <VisitTracker />
      <Header />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/assessment" element={<Assessment />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
      <footer className="text-center text-sm text-gray-500 py-6">GrowthPilot AI</footer>
    </div>
  )
}
