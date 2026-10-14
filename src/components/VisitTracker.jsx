import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { trackVisit } from '../services/api'
import { getAcquisitionSource, getVisitorId } from '../services/visitor'

export default function VisitTracker() {
  const location = useLocation()

  useEffect(() => {
    trackVisit({
      visitor_id: getVisitorId(),
      path: location.pathname,
      source: getAcquisitionSource(),
    }).catch((error) => {
      console.error('Could not record the page visit.', error)
    })
  }, [location.pathname])

  return null
}
