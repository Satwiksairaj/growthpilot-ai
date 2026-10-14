import React from 'react'

export default function Alert({variant = 'info', children}){
  const colors = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    error: 'bg-red-50 border-red-200 text-red-800'
  }
  return (
    <div className={`border-l-4 p-3 ${colors[variant] || colors.info}`} role="alert">
      {children}
    </div>
  )
}
