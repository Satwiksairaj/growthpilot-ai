let sessionVisitorId

export function getVisitorId() {
  if (sessionVisitorId) return sessionVisitorId

  try {
    const storedVisitorId = window.localStorage.getItem('growthpilot-visitor-id')
    if (storedVisitorId) {
      sessionVisitorId = storedVisitorId
      return storedVisitorId
    }

    sessionVisitorId = window.crypto.randomUUID()
    window.localStorage.setItem('growthpilot-visitor-id', sessionVisitorId)
    return sessionVisitorId
  } catch (error) {
    console.error('Could not persist the analytics visitor ID.', error)
    sessionVisitorId = window.crypto.randomUUID()
    return sessionVisitorId
  }
}

export function getAcquisitionSource() {
  const params = new URLSearchParams(window.location.search)
  const medium = params.get('utm_medium')?.toLowerCase()
  const source = params.get('utm_source')?.toLowerCase()
  if (['cpc', 'ppc', 'paid', 'display'].includes(medium)) return 'paid'
  if (['google', 'bing', 'yahoo', 'duckduckgo'].includes(source)) return 'organic'
  if (['facebook', 'instagram', 'linkedin', 'tiktok', 'social'].includes(source)) return 'social'

  const referrer = document.referrer
  if (!referrer) return 'direct'
  try {
    const host = new URL(referrer).hostname.toLowerCase()
    if (['google.', 'bing.', 'yahoo.', 'duckduckgo.'].some((domain) => host.includes(domain))) {
      return 'organic'
    }
    if (['facebook.', 'instagram.', 'linkedin.', 'tiktok.'].some((domain) => host.includes(domain))) {
      return 'social'
    }
    return 'referral'
  } catch (error) {
    console.error('Could not classify the referring page.', error)
    return 'referral'
  }
}
