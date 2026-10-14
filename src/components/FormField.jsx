import React from 'react'

export default function FormField({label, children, required, id}){
  return (
    <div className="mb-4">
      {label && <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">{label}{required && <span className="text-red-500"> *</span>}</label>}
      {children}
    </div>
  )
}
