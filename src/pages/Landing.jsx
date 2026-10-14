import React from 'react'
import { Link } from 'react-router-dom'
import Container from '../components/Container'
import Button from '../components/Button'

export default function Landing(){
  return (
    <div className="pt-16">
      <Container>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
          <section>
            <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900">Discover Your Technology Path with AI</h1>
            <p className="mt-6 text-lg text-gray-600">GrowthPilot AI helps students and institutions match skills, interests, and pathways using intelligent assessments and growth analytics. Get a personalized learning path and insights to accelerate student outcomes.</p>
            <div className="mt-8 flex gap-3">
              <Link to="/assessment"><Button>Discover My Path</Button></Link>
              <Link to="/dashboard" className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-blue-700 bg-blue-100 hover:bg-blue-200">View Dashboard</Link>
            </div>
            <p className="mt-4 text-xs text-gray-500">Development build. Dashboard metrics reflect local events recorded by this instance.</p>
          </section>

          <aside className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-xl font-semibold mb-3">How it works</h3>
            <ol className="list-decimal list-inside text-gray-600">
              <li>Complete a short assessment about interests and experience</li>
              <li>Receive a tailored technology learning path and report</li>
              <li>Institutions get growth analytics to improve acquisition</li>
            </ol>
          </aside>
        </div>
      </Container>
    </div>
  )
}
