import React from 'react'

export default function Button({children, onClick, className = '', type = 'button', disabled}){
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 ${className}`}
    >
      {children}
    </button>
  )
}
