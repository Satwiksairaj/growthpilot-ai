import React from 'react'

export default function Loading({label = 'Loading...'}){
  return (
    <div className="flex items-center gap-3 text-gray-600">
      <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      <div>{label}</div>
    </div>
  )
}
