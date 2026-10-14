// import React, { useEffect, useState } from 'react'
// import Container from '../components/Container'
// import Alert from '../components/Alert'
// import Loading from '../components/Loading'
// import { fetchMetrics } from '../services/api'
// import { PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts'

// const COLORS = ['#3182CE','#2B6CB0','#63B3ED','#90CDF4']

// function MetricCard({label, value}){
//   return (
//     <div className="bg-white rounded-lg shadow p-4">
//       <div className="text-sm text-gray-500">{label}</div>
//       <div className="text-2xl font-semibold">{value}</div>
//     </div>
//   )
// }

// function formatRate(value) {
//   return value === null || value === undefined ? 'Not tracked' : `${(value * 100).toFixed(1)}%`
// }

// export default function Dashboard(){
//   const [data, setData] = useState(null)
//   const [loading, setLoading] = useState(true)
//   const [error, setError] = useState(null)
//   const [refreshKey, setRefreshKey] = useState(0)

//   useEffect(()=>{
//     let cancelled = false
//     setLoading(true)
//     setError(null)
//     fetchMetrics().then((res)=>{
//       if (!cancelled) setData(res)
//     }).catch((err)=>{
//       console.error(err)
//       if (!cancelled) setError(err.message || 'Failed to load metrics.')
//     }).finally(()=>{
//       if (!cancelled) setLoading(false)
//     })
//     return ()=> { cancelled = true }
//   },[refreshKey])

//   if(loading) return <div className="pt-8"><Container><Loading label="Loading dashboard..." /></Container></div>
//   if(error) return (
//     <div className="pt-8">
//       <Container>
//         <Alert variant="error">Could not load live dashboard data: {error}</Alert>
//         <button type="button" className="mt-4 text-sm text-blue-700 underline" onClick={()=>setRefreshKey((key)=>key + 1)}>Try again</button>
//       </Container>
//     </div>
//   )

//   const m = data.metrics
//   const sources = data.sources
//   const funnel = data.funnel
//   const rates = m.conversion_rates || {}
//   const conversion = formatRate(rates.visitors_to_leads)

//   return (
//     <div className="pt-8 pb-12">
//       <Container>
//         <div className="flex justify-between items-center mb-4">
//           <h2 className="text-2xl font-semibold">Growth Dashboard</h2>
//           <div className="text-sm text-gray-500">{data.note}</div>
//         </div>

//         {data.empty && (
//           <Alert variant="info">
//             No live analytics events have been recorded yet. Browse the assessment and submit a report to populate this development dashboard.
//           </Alert>
//         )}

//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
//           <MetricCard label="Visitors" value={m.visitors} />
//           <MetricCard label="Assessment starts" value={m.starts} />
//           <MetricCard label="Assessment submissions" value={m.submissions ?? m.completions} />
//           <MetricCard label="Reports generated" value={m.reports} />
//           <MetricCard label="Consented leads captured" value={m.leads} />
//           <MetricCard label="Qualified leads" value={m.qualified ?? 'Not configured'} />
//         </div>

//         <div className="mb-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
//           <MetricCard label="Visitors → leads" value={formatRate(rates.visitors_to_leads)} />
//           <MetricCard label="Assessment starts → completions" value={formatRate(rates.starts_to_completions)} />
//           <MetricCard label="Completed reports → consented leads" value={formatRate(rates.completions_to_leads)} />
//         </div>

//         <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
//           <div className="lg:col-span-2 bg-white rounded-lg shadow p-4">
//             <h3 className="text-lg font-medium mb-2">Local activity counts (not a user-level funnel)</h3>
//             {m.visitors === 0 && m.starts === 0 && m.completions === 0 ? (
//               <p className="flex h-[300px] items-center justify-center text-sm text-gray-500">Funnel data will appear after real local events are recorded.</p>
//             ) : (
//               <div style={{width: '100%', height: 300}}>
//                 <ResponsiveContainer>
//                   <BarChart data={funnel} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
//                     <CartesianGrid strokeDasharray="3 3" />
//                     <XAxis dataKey="stage" />
//                     <YAxis allowDecimals={false} />
//                     <Tooltip />
//                     <Bar dataKey="value" fill="#3182CE">
//                       {funnel.map((entry, idx)=>(<Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />))}
//                     </Bar>
//                   </BarChart>
//                 </ResponsiveContainer>
//               </div>
//             )}
//           </div>

//           <div className="bg-white rounded-lg shadow p-4">
//             <h3 className="text-lg font-medium mb-2">Acquisition sources</h3>
//             {m.visitors === 0 ? (
//               <p className="flex h-[260px] items-center justify-center text-sm text-gray-500">No acquisition-source events yet.</p>
//             ) : (
//               <div style={{width: '100%', height: 260}}>
//                 <ResponsiveContainer>
//                   <PieChart>
//                     <Pie data={sources.filter((source) => source.value > 0)} dataKey="value" nameKey="name" outerRadius={90} fill="#8884d8" label>
//                       {sources.filter((source) => source.value > 0).map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
//                     </Pie>
//                     <Tooltip />
//                   </PieChart>
//                 </ResponsiveContainer>
//               </div>
//             )}
//             <div className="mt-3 text-sm text-gray-600">Source attribution is approximate; IDs are pseudonymous, not authenticated identities.</div>
//           </div>
//         </div>
//         <p className="mt-5 text-xs text-gray-500">Data mode: {data.mode === 'live' ? 'live local measurements (development only)' : 'unknown'}. Visitor-to-lead and start-to-completion rates are not tracked because visitor IDs are not linked to assessment submissions. Qualified leads are not configured.</p>

//       </Container>
//     </div>
//   )
// }


import React, { useEffect, useState } from 'react'
import Container from '../components/Container'
import Alert from '../components/Alert'
import Loading from '../components/Loading'
import { fetchMetrics } from '../services/api'

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts'

const COLORS = ['#3182CE', '#2B6CB0', '#63B3ED', '#90CDF4']

function MetricCard({ label, value, detail }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
      {detail && <div className="mt-1 text-xs text-gray-500">{detail}</div>}
    </div>
  )
}

function formatRate(value, denominator) {
  if (
    typeof value !== 'number' ||
    !Number.isFinite(value) ||
    value < 0 ||
    value > 1
  ) {
    return denominator === 0 ? 'Awaiting data' : 'Unavailable'
  }

  return `${(value * 100).toFixed(1)}%`
}

export default function Dashboard() {
  const frontendPreview = import.meta.env.VITE_FRONTEND_PREVIEW === 'true'
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function loadMetrics() {
      if (frontendPreview) {
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const result = await fetchMetrics()

        if (!result || !result.metrics) {
          throw new Error('Invalid analytics response from the server.')
        }

        if (!cancelled) {
          setData(result)
        }
      } catch (err) {
        console.error('Dashboard metrics error:', err)

        if (!cancelled) {
          setError(
            err.message || 'Failed to load dashboard metrics.'
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadMetrics()

    return () => {
      cancelled = true
    }
  }, [frontendPreview, refreshKey])

  if (frontendPreview) {
    return (
      <div className="pt-8">
        <Container>
          <h2 className="mb-4 text-2xl font-semibold">Growth Dashboard</h2>
          <Alert variant="info">
            Frontend-only preview: live metrics are unavailable because this deployment does not include the API or its database.
          </Alert>
        </Container>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="pt-8">
        <Container>
          <Loading label="Loading dashboard..." />
        </Container>
      </div>
    )
  }

  if (error || !data?.metrics) {
    return (
      <div className="pt-8">
        <Container>
          <Alert variant="error">
            Could not load live dashboard data:{' '}
            {error || 'Missing analytics data.'}
          </Alert>

          <button
            type="button"
            className="mt-4 text-sm text-blue-700 underline"
            onClick={() => setRefreshKey(key => key + 1)}
          >
            Try again
          </button>
        </Container>
      </div>
    )
  }

  const m = data.metrics
  const rates = m.conversion_rates || {}
  const rateCounts = m.conversion_rate_counts || {}
  const rateDetail = key => {
    const counts = rateCounts[key]
    if (
      !counts ||
      !Number.isInteger(counts.numerator) ||
      !Number.isInteger(counts.denominator)
    ) {
      return 'Linked conversion counts are not available.'
    }
    return `${counts.numerator} / ${counts.denominator} linked records`
  }

  const sources = Array.isArray(data.sources)
    ? data.sources.filter(
        source =>
          source &&
          typeof source.name === 'string' &&
          typeof source.value === 'number' &&
          Number.isFinite(source.value) &&
          source.value > 0
      )
    : []

  const funnel = Array.isArray(data.funnel)
    ? data.funnel.filter(
        item =>
          item &&
          typeof item.stage === 'string' &&
          typeof item.value === 'number' &&
          Number.isFinite(item.value) &&
          item.value >= 0
      )
    : []

  const hasActivity = funnel.some(item => item.value > 0)

  return (
    <div className="pt-8 pb-12">
      <Container>
        <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
          <h2 className="text-2xl font-semibold">
            Growth Dashboard
          </h2>

          <div className="text-sm text-gray-500">
            {data.note}
          </div>
        </div>

        {data.empty && (
          <Alert variant="info">
            No live analytics events have been recorded yet.
            Browse the assessment and submit a report to populate
            this development dashboard.
          </Alert>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <MetricCard label="Visitors" value={m.visitors ?? 0} />
          <MetricCard label="Assessment starts" value={m.starts ?? 0} />
          <MetricCard
            label="Assessment submissions"
            value={m.submissions ?? m.completions ?? 0}
          />
          <MetricCard label="Reports generated" value={m.reports ?? 0} />
          <MetricCard
            label="Consented leads captured"
            value={m.leads ?? 0}
          />
          <MetricCard
            label="Qualified leads (demo proxy)"
            value={m.qualified ?? 'Not configured'}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <MetricCard
            label="Visitors → leads"
            value={formatRate(
              rates.visitors_to_leads,
              rateCounts.visitors_to_leads?.denominator
            )}
            detail={rateDetail('visitors_to_leads')}
          />
          <MetricCard
            label="Tracked assessment starts → reports"
            value={formatRate(
              rates.starts_to_completions,
              rateCounts.starts_to_completions?.denominator
            )}
            detail={rateDetail('starts_to_completions')}
          />
          <MetricCard
            label="Completed reports → consented leads"
            value={formatRate(
              rates.completions_to_leads,
              rateCounts.completions_to_leads?.denominator
            )}
            detail={rateDetail('completions_to_leads')}
          />
        </div>
        <p className="mb-6 text-xs text-gray-500">
          To populate these rates, visit Assessment and submit a report. Add contact details and consent to count as a lead. Past records without visitor links are excluded.
        </p>
        <p className="mb-6 text-xs text-gray-500">
          Qualified-lead demo proxy: high-school stage, consented contact, and a saved report. This is not NIAT’s official qualification rule.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-medium mb-2">
              Recorded activity counts (not a user-level funnel)
            </h3>

            {!hasActivity ? (
              <p className="flex h-[300px] items-center justify-center text-sm text-gray-500">
                Funnel data will appear after real local events are recorded.
              </p>
            ) : (
              <div className="w-full h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={funnel}
                    margin={{
                      top: 5,
                      right: 20,
                      left: 0,
                      bottom: 5,
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="stage" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#3182CE">
                      {funnel.map((entry, index) => (
                        <Cell
                          key={`funnel-${entry.stage}-${index}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-medium mb-2">
              Acquisition sources
            </h3>

            {sources.length === 0 ? (
              <p className="flex h-[260px] items-center justify-center text-sm text-gray-500">
                No acquisition-source events yet.
              </p>
            ) : (
              <div className="w-full h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sources}
                      dataKey="value"
                      nameKey="name"
                      outerRadius={90}
                      label
                    >
                      {sources.map((source, index) => (
                        <Cell
                          key={`source-${source.name}-${index}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="mt-3 text-sm text-gray-600">
              Source attribution is approximate; IDs are
              pseudonymous, not authenticated identities.
            </div>
          </div>
        </div>

        <p className="mt-5 text-xs text-gray-500">
          Data mode:{' '}
          {data.mode === 'live'
            ? 'live local measurements (development only)'
            : 'unknown'}.
          {' '}Linked conversion rates cover tracked activity since {data.tracking_since || 'tracking was enabled'}; older records are excluded.
          {' '}Qualified leads use the labeled demo proxy above, not official admissions criteria.
        </p>
      </Container>
    </div>
  )
}
