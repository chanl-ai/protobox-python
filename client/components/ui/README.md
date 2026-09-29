# UI Components Usage Guide

This document outlines how to use the custom UI components that replace browser alerts and confirmations.

## ConfirmationDialog

A reusable confirmation dialog that replaces `confirm()` calls.

### Usage

```typescript
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog"

const [showConfirm, setShowConfirm] = useState(false)

// Show confirmation
const handleDelete = () => {
  setShowConfirm(true)
}

// Handle confirmation
const handleConfirmDelete = () => {
  // Delete logic here
  console.log("Item deleted")
}

// In JSX
<ConfirmationDialog
  open={showConfirm}
  onOpenChange={setShowConfirm}
  title="Delete Item"
  description="Are you sure you want to delete this item? This action cannot be undone."
  confirmText="Delete"
  cancelText="Cancel"
  variant="destructive"
  onConfirm={handleConfirmDelete}
/>
```

### Props

- `open: boolean` - Controls dialog visibility
- `onOpenChange: (open: boolean) => void` - Callback when dialog state changes
- `title: string` - Dialog title
- `description?: string` - Optional description text
- `confirmText?: string` - Confirm button text (default: "Confirm")
- `cancelText?: string` - Cancel button text (default: "Cancel")
- `variant?: "default" | "destructive" | "success" | "info"` - Visual variant
- `onConfirm: () => void` - Callback when confirmed
- `onCancel?: () => void` - Optional callback when cancelled

### Variants

- `default` - Blue info icon, default button
- `destructive` - Red warning icon, destructive button
- `success` - Green check icon, default button
- `info` - Orange X icon, default button

## ToastNotification & useToast

Toast notifications that replace `alert()` calls.

### Usage

```typescript
import { useToast } from "@/components/ui/toast-notification"

const MyComponent = () => {
  const { toast, ToastContainer } = useToast()

  const handleSuccess = () => {
    toast("Operation completed successfully!", "success")
  }

  const handleError = () => {
    toast("Something went wrong. Please try again.", "error")
  }

  return (
    <div>
      <button onClick={handleSuccess}>Success</button>
      <button onClick={handleError}>Error</button>
      
      {/* Add this once per component tree */}
      <ToastContainer />
    </div>
  )
}
```

### Toast Types

- `success` - Green with check icon
- `error` - Red with X icon
- `info` - Blue with info icon
- `warning` - Orange with warning icon

### Toast Function

```typescript
toast(message: string, type?: "success" | "error" | "info" | "warning")
```

## ErrorDialog

A specialized dialog for showing detailed error messages.

### Usage

```typescript
import { ErrorDialog } from "@/components/ui/error-dialog"

const [showError, setShowError] = useState(false)
const [errorDetails, setErrorDetails] = useState("")

const handleApiError = async () => {
  try {
    await apiCall()
  } catch (error) {
    setErrorDetails(error.message)
    setShowError(true)
  }
}

const handleRetry = () => {
  // Retry logic here
  handleApiError()
}

// In JSX
<ErrorDialog
  open={showError}
  onOpenChange={setShowError}
  title="API Error"
  message="Failed to load data from the server."
  details={errorDetails}
  onRetry={handleRetry}
  retryText="Try Again"
/>
```

### Props

- `open: boolean` - Controls dialog visibility
- `onOpenChange: (open: boolean) => void` - Callback when dialog state changes
- `title?: string` - Dialog title (default: "Error")
- `message: string` - Main error message
- `details?: string` - Optional technical details (shown in monospace)
- `onRetry?: () => void` - Optional retry callback
- `retryText?: string` - Retry button text (default: "Retry")

## Migration Examples

### Before (Browser Alerts)

```typescript
// Old way - browser confirm
const handleDelete = () => {
  if (confirm("Are you sure you want to delete this item?")) {
    deleteItem()
  }
}

// Old way - browser alert
const handleError = (error: string) => {
  alert(`Error: ${error}`)
}
```

### After (Shadcn Dialogs)

```typescript
// New way - confirmation dialog
const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

const handleDelete = () => {
  setShowDeleteConfirm(true)
}

const handleConfirmDelete = () => {
  deleteItem()
}

// New way - toast notification
const { toast } = useToast()

const handleError = (error: string) => {
  toast(`Error: ${error}`, "error")
}

// In JSX
<ConfirmationDialog
  open={showDeleteConfirm}
  onOpenChange={setShowDeleteConfirm}
  title="Delete Item"
  description="Are you sure you want to delete this item?"
  variant="destructive"
  onConfirm={handleConfirmDelete}
/>
```

## Best Practices

1. **Use confirmation dialogs for destructive actions** (delete, reset, etc.)
2. **Use toasts for feedback messages** (success, error, info)
3. **Use error dialogs for detailed error information** with retry options
4. **Keep confirmation text clear and specific** - avoid generic "Are you sure?"
5. **Place ToastContainer once per page/layout** to avoid duplicates
6. **Use appropriate variants** for visual consistency (destructive for deletes, success for saves)