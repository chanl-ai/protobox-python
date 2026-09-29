import { useState, useEffect } from 'react'

export interface Toast {
  id: string
  title?: string
  description?: string
  variant?: 'default' | 'destructive'
  duration?: number
}

interface ToastState {
  toasts: Toast[]
}

const listeners: Array<(state: ToastState) => void> = []
let memoryState: ToastState = { toasts: [] }

function dispatch(action: { type: 'ADD_TOAST' | 'REMOVE_TOAST'; toast?: Toast; id?: string }) {
  switch (action.type) {
    case 'ADD_TOAST':
      memoryState = {
        toasts: [...memoryState.toasts, action.toast!],
      }
      break
    case 'REMOVE_TOAST':
      memoryState = {
        toasts: memoryState.toasts.filter((t) => t.id !== action.id),
      }
      break
  }
  
  listeners.forEach((listener) => {
    listener(memoryState)
  })
}

let toastCount = 0

export function toast(props: Omit<Toast, 'id'>) {
  const id = String(toastCount++)
  const duration = props.duration ?? 5000
  
  dispatch({
    type: 'ADD_TOAST',
    toast: {
      ...props,
      id,
      duration,
    },
  })
  
  if (duration > 0) {
    setTimeout(() => {
      dispatch({ type: 'REMOVE_TOAST', id })
    }, duration)
  }
  
  return id
}

export function useToast() {
  const [state, setState] = useState<ToastState>(memoryState)

  useEffect(() => {
    listeners.push(setState)
    return () => {
      const index = listeners.indexOf(setState)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }, [state])

  return {
    ...state,
    toast,
    dismiss: (id: string) => dispatch({ type: 'REMOVE_TOAST', id }),
  }
}