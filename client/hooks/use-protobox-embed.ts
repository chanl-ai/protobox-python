"use client"

import { useState, useEffect, useCallback } from 'react'
import { ProtoBoxPartnerClient } from '@/lib/partner-sdk'

interface Integration {
  id: string
  type: string
  name: string
  description: string
  icon?: string
  is_connected: boolean
  connected_at?: string
  config?: Record<string, any>
  status?: 'connected' | 'error' | 'disconnected'
}

interface UseProtoBoxEmbedOptions {
  partnerId: string
  partnerUserId: string
  secretKey: string
  apiUrl?: string
}

export function useProtoBoxEmbed({
  partnerId,
  partnerUserId,
  secretKey,
  apiUrl = '/api/partner'
}: UseProtoBoxEmbedOptions) {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // Initialize SDK
  const sdk = new ProtoBoxPartnerClient({
    partnerId,
    secretKey,
    apiUrl
  })

  // Fetch integrations
  const fetchIntegrations = useCallback(async () => {
    try {
      setLoading(true)
      const response = await sdk.getIntegrations(partnerUserId)
      
      // Transform the response to match our Integration interface
      const transformedIntegrations = response.integrations.map((integration: any) => ({
        id: integration.id,
        type: integration.integration_type,
        name: integration.name,
        description: integration.description || '',
        is_connected: integration.is_connected || false,
        connected_at: integration.connected_at,
        config: integration.config || {},
        status: integration.is_connected ? 'connected' : 'disconnected'
      }))
      
      setIntegrations(transformedIntegrations)
      setError(null)
    } catch (err) {
      setError(err as Error)
    } finally {
      setLoading(false)
    }
  }, [sdk, partnerUserId])

  // Connect integration
  const connect = useCallback(async (integrationType: string) => {
    try {
      // Start OAuth flow
      const { oauth_url } = await sdk.startOAuth(partnerUserId, {
        integration_type: integrationType,
        redirect_uri: window.location.origin + '/oauth/callback'
      })
      
      // Open OAuth popup
      const popup = window.open(
        oauth_url,
        'oauth-popup',
        'width=600,height=700,left=100,top=100'
      )
      
      // Wait for OAuth completion
      return new Promise<{ success: boolean }>((resolve) => {
        const checkInterval = setInterval(() => {
          if (popup?.closed) {
            clearInterval(checkInterval)
            // Refresh integrations after popup closes
            fetchIntegrations()
            resolve({ success: true })
          }
        }, 500)
        
        // Also listen for postMessage from OAuth callback
        const handleMessage = (event: MessageEvent) => {
          if (event.data.type === 'oauth-complete') {
            clearInterval(checkInterval)
            window.removeEventListener('message', handleMessage)
            popup?.close()
            fetchIntegrations()
            resolve({ success: true })
          }
        }
        window.addEventListener('message', handleMessage)
      })
    } catch (err) {
      setError(err as Error)
      throw err
    }
  }, [sdk, partnerUserId, fetchIntegrations])

  // Disconnect integration
  const disconnect = useCallback(async (integrationId: string) => {
    try {
      await sdk.disconnectIntegration(partnerUserId, integrationId)
      // Refresh integrations
      await fetchIntegrations()
    } catch (err) {
      setError(err as Error)
      throw err
    }
  }, [sdk, partnerUserId, fetchIntegrations])

  // Load integrations on mount
  useEffect(() => {
    fetchIntegrations()
  }, [fetchIntegrations])

  return {
    integrations,
    loading,
    error,
    connect,
    disconnect,
    refresh: fetchIntegrations
  }
}