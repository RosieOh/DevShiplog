'use client'

import React from 'react'
import { useToastStore } from '@/store/toastStore'

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ComponentType<{ error: Error; resetError: () => void }>
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    // Toast는 클라이언트 컴포넌트에서 처리
  }

  resetError = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        const Fallback = this.props.fallback
        return <Fallback error={this.state.error} resetError={this.resetError} />
      }

      return (
        <div className="bg-[#f9f9f7] min-h-screen flex items-center justify-center px-[5%]">
          <div className="max-w-2xl w-full text-center">
            <div className="mb-8">
              <div className="w-20 h-20 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-[#111111] mb-4">오류가 발생했습니다</h2>
              <p className="text-lg text-[#666666] mb-4">
                {this.state.error.message || '예상치 못한 오류가 발생했습니다.'}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={this.resetError}
                className="px-8 py-4 bg-[#d1fb52] text-black rounded-full font-semibold hover:scale-105 transition-transform"
              >
                다시 시도
              </button>
              <a
                href="/dashboard"
                className="px-8 py-4 bg-white text-[#111111] border border-black/10 rounded-full font-semibold hover:scale-105 transition-transform"
              >
                Dashboard로 가기
              </a>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

