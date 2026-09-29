/**
 * Centralized toast utility using Sonner
 * This provides a consistent API for all toast notifications across the app
 */
import { toast as sonnerToast, ExternalToast } from "sonner"

type ToastOptions = ExternalToast & {
  centered?: boolean
}

export const toast = {
  /**
   * Show a success toast
   */
  success: (message: string, options?: ToastOptions) => {
    const { centered, ...rest } = options || {}
    return sonnerToast.success(message, {
      position: centered ? "top-center" : undefined,
      ...rest,
    })
  },

  /**
   * Show an error toast
   */
  error: (message: string, options?: ToastOptions) => {
    const { centered, ...rest } = options || {}
    return sonnerToast.error(message, {
      position: centered ? "top-center" : undefined,
      ...rest,
    })
  },

  /**
   * Show an info toast
   */
  info: (message: string, options?: ToastOptions) => {
    const { centered, ...rest } = options || {}
    return sonnerToast.info(message, {
      position: centered ? "top-center" : undefined,
      ...rest,
    })
  },

  /**
   * Show a warning toast
   */
  warning: (message: string, options?: ToastOptions) => {
    const { centered, ...rest } = options || {}
    return sonnerToast.warning(message, {
      position: centered ? "top-center" : undefined,
      ...rest,
    })
  },

  /**
   * Show a loading toast that can be updated
   */
  loading: (message: string, options?: ToastOptions) => {
    const { centered, ...rest } = options || {}
    return sonnerToast.loading(message, {
      position: centered ? "top-center" : undefined,
      ...rest,
    })
  },

  /**
   * Show a promise-based toast
   * Automatically shows loading → success/error states
   */
  promise: <T,>(
    promise: Promise<T>,
    messages: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((error: any) => string)
    },
    options?: ToastOptions
  ) => {
    const { centered, ...rest } = options || {}
    return sonnerToast.promise(promise, messages, {
      position: centered ? "top-center" : undefined,
      ...rest,
    })
  },

  /**
   * Dismiss a toast by ID or dismiss all toasts
   */
  dismiss: (id?: string | number) => {
    return sonnerToast.dismiss(id)
  },

  /**
   * Show a custom toast with full control
   */
  custom: (message: React.ReactNode, options?: ToastOptions) => {
    const { centered, ...rest } = options || {}
    return sonnerToast.custom(message, {
      position: centered ? "top-center" : undefined,
      ...rest,
    })
  },
}

// Export convenience functions for common patterns
export const showSuccessToast = (message: string) => toast.success(message, { centered: true })
export const showErrorToast = (message: string) => toast.error(message)
export const showLoadingToast = (message: string) => toast.loading(message)