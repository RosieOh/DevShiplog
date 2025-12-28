'use client'

import { useEffect } from 'react'
import { useToastStore } from '@/store/toastStore'

export default function Toast() {
  const { toasts, removeToast } = useToastStore()

  useEffect(() => {
    toasts.forEach((toast) => {
      if (toast.autoClose) {
        const timer = setTimeout(() => {
          removeToast(toast.id)
        }, toast.duration || 3000)
        return () => clearTimeout(timer)
      }
    })
  }, [toasts, removeToast])

  return (
    <div className="fixed top-20 right-5 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`min-w-[300px] p-4 rounded-2xl shadow-lg border ${
            toast.type === 'success'
              ? 'bg-[#d1fb52] text-black border-[#d1fb52]'
              : toast.type === 'error'
              ? 'bg-red-50 text-red-700 border-red-200'
              : toast.type === 'warning'
              ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
              : 'bg-white text-[#111111] border-black/10'
          }`}
        >
          <div className="flex items-start justify-between gap-4">
            <p className="font-semibold flex-1">{toast.message}</p>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-current opacity-70 hover:opacity-100 transition-opacity"
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

