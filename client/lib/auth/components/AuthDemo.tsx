"use client"

import React from 'react'
import { useAuth } from '../hooks/useAuth'
import { LoginForm } from './forms/LoginForm'

export function AuthDemo() {
  const { user, loading } = useAuth()
  
  return (
    <div className="space-y-8">
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Auth Context Status</h2>
        <div className="space-y-2">
          <div>
            <span className="font-medium">Loading:</span> {loading ? 'true' : 'false'}
          </div>
          <div>
            <span className="font-medium">User:</span> {user ? user.email : 'null'}
          </div>
        </div>
      </div>
      
      {!user && (
        <div>
          <h3 className="text-lg font-semibold mb-4">Login Form Component</h3>
          <LoginForm />
        </div>
      )}
    </div>
  )
}