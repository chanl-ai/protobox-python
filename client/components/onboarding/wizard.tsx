"use client"

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { IconArrowLeft, IconArrowRight, IconCheck } from '@tabler/icons-react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface WizardStep {
  id: string
  title: string
  description?: string
  icon?: React.ReactNode
  content: React.ReactNode | ((props: { data: any; updateData: (key: string, value: any) => void; errors: any; stepId: string }) => React.ReactNode)
  validate?: (data: any) => boolean | string // Returns true if valid, or error message
  optional?: boolean
  skipLabel?: string // Label for skip button if optional
}

interface WizardProps {
  steps: WizardStep[]
  onComplete: (data: any) => Promise<void>
  onStepChange?: (step: number, data: any) => void
  initialData?: any
  title?: string
  className?: string
  showProgress?: boolean
  allowSkip?: boolean
  completingText?: string
  completeText?: string
}

const slideVariants = {
  enter: {
    opacity: 0,
    scale: 0.95,
    y: 10
  },
  center: {
    zIndex: 1,
    opacity: 1,
    scale: 1,
    y: 0
  },
  exit: {
    zIndex: 0,
    opacity: 0,
    scale: 0.95,
    y: -10
  }
}

const swipeConfidenceThreshold = 10000
const swipePower = (offset: number, velocity: number) => {
  return Math.abs(offset) * velocity
}

export function OnboardingWizard({
  steps,
  onComplete,
  onStepChange,
  initialData = {},
  title,
  className,
  showProgress = true,
  allowSkip = true,
  completingText = "Setting up...",
  completeText = "Complete"
}: WizardProps) {
  const [[currentStep, direction], setCurrentStep] = useState([0, 0])
  const [data, setData] = useState(initialData)
  const [errors, setErrors] = useState<{ [key: string]: string }>({})
  const [loading, setLoading] = useState(false)

  // Update data when initialData changes
  useEffect(() => {
    setData(initialData)
  }, [initialData])

  const currentStepData = steps[currentStep]
  const isLastStep = currentStep === steps.length - 1
  const isFirstStep = currentStep === 0
  const progress = ((currentStep + 1) / steps.length) * 100

  const updateData = (key: string, value: any) => {
    setData((prev: any) => ({ ...prev, [key]: value }))
    // Clear error for this field
    setErrors(prev => ({ ...prev, [key]: '' }))
  }

  const validateStep = () => {
    if (currentStepData.validate) {
      const result = currentStepData.validate(data)
      if (result !== true) {
        setErrors({ [currentStepData.id]: result as string })
        return false
      }
    }
    return true
  }

  const handleNext = async () => {
    // Skip validation if step is optional and user is skipping
    if (!currentStepData.optional && !validateStep()) {
      return
    }

    if (isLastStep) {
      setLoading(true)
      try {
        await onComplete(data)
      } catch (error) {
      } finally {
        setLoading(false)
      }
    } else {
      paginate(1)
      onStepChange?.(currentStep + 1, data)
    }
  }

  const handleBack = () => {
    if (!isFirstStep) {
      paginate(-1)
      onStepChange?.(currentStep - 1, data)
    }
  }

  const handleSkip = () => {
    if (currentStepData.optional && !isLastStep) {
      paginate(1)
      onStepChange?.(currentStep + 1, data)
    }
  }

  const paginate = (newDirection: number) => {
    setCurrentStep([currentStep + newDirection, newDirection])
  }

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleNext()
      } else if (e.key === 'Escape' && !isFirstStep) {
        handleBack()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentStep, data])

  return (
    <div className={cn("w-full max-w-2xl mx-auto", className)}>
      <Card className="border-0 shadow-lg">
        {/* Progress Bar */}
        {showProgress && (
          <div className="px-6 pt-6">
            <Progress value={progress} className="h-2" />
            <p className="text-xs text-muted-foreground mt-2">
              Step {currentStep + 1} of {steps.length}
            </p>
          </div>
        )}

        {/* Header */}
        <CardHeader className="text-center pb-2">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentStep}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{
                x: { type: "spring", stiffness: 300, damping: 30 },
                opacity: { duration: 0.2 }
              }}
            >
              {currentStepData.icon && (
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                  {currentStepData.icon}
                </div>
              )}
              <CardTitle className="text-2xl">{currentStepData.title}</CardTitle>
              {currentStepData.description && (
                <CardDescription className="mt-2 text-base">
                  {currentStepData.description}
                </CardDescription>
              )}
            </motion.div>
          </AnimatePresence>
        </CardHeader>

        {/* Content */}
        <CardContent className="px-6 py-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{
                opacity: { duration: 0.3 },
                scale: { duration: 0.3, type: "spring", stiffness: 300, damping: 30 },
                y: { duration: 0.3, type: "spring", stiffness: 300, damping: 30 }
              }}
            >
              <div className="space-y-4">
                {typeof currentStepData.content === 'function' 
                  ? currentStepData.content({ data, updateData, errors, stepId: currentStepData.id })
                  : React.isValidElement(currentStepData.content)
                    ? React.cloneElement(currentStepData.content as React.ReactElement, {
                        data,
                        updateData,
                        errors,
                        stepId: currentStepData.id
                      })
                    : currentStepData.content}
              </div>
            </motion.div>
          </AnimatePresence>
        </CardContent>

        {/* Footer */}
        <CardFooter className="flex justify-between px-6 pb-6">
          <div className="flex gap-2">
            {!isFirstStep && (
              <Button
                variant="outline"
                onClick={handleBack}
                disabled={loading}
              >
                <IconArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
            )}
            {currentStepData.optional && !isLastStep && allowSkip && (
              <Button
                variant="ghost"
                onClick={handleSkip}
                disabled={loading}
              >
                {currentStepData.skipLabel || 'Skip'}
              </Button>
            )}
          </div>

          <Button 
            onClick={handleNext} 
            disabled={loading}
            className="min-w-[120px]"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {completingText}
              </>
            ) : isLastStep ? (
              <>
                <IconCheck className="mr-2 h-4 w-4" />
                {completeText}
              </>
            ) : (
              <>
                Next
                <IconArrowRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </CardFooter>
      </Card>

      {/* Step indicators */}
      <div className="flex justify-center mt-6 gap-2">
        {steps.map((_, index) => (
          <button
            key={index}
            onClick={() => {
              if (index < currentStep || (index === currentStep)) {
                setCurrentStep([index, index > currentStep ? 1 : -1])
              }
            }}
            className={cn(
              "h-2 rounded-full transition-all duration-300",
              index === currentStep 
                ? "w-8 bg-primary" 
                : index < currentStep 
                  ? "w-2 bg-primary/50 hover:bg-primary/70" 
                  : "w-2 bg-muted hover:bg-muted-foreground/30",
              index <= currentStep && "cursor-pointer"
            )}
            disabled={index > currentStep}
          />
        ))}
      </div>
    </div>
  )
}

// Individual question components for common patterns
export function TextInput({ 
  data, 
  updateData, 
  errors, 
  stepId,
  label,
  placeholder,
  type = 'text',
  required = false,
  maxLength,
  pattern,
  helperText
}: any) {
  return (
    <div className="space-y-2">
      {label && (
        <label className="text-sm font-medium">
          {label} {required && <span className="text-destructive">*</span>}
        </label>
      )}
      <input
        type={type}
        value={data?.[stepId] || ''}
        onChange={(e) => updateData(stepId, e.target.value)}
        placeholder={placeholder}
        maxLength={maxLength}
        pattern={pattern}
        className={cn(
          "w-full px-3 py-2 border rounded-md",
          "focus:outline-none focus:ring-2 focus:ring-primary",
          errors?.[stepId] && "border-destructive"
        )}
      />
      {helperText && !errors?.[stepId] && (
        <p className="text-sm text-muted-foreground">{helperText}</p>
      )}
      {errors?.[stepId] && (
        <p className="text-sm text-destructive">{errors[stepId]}</p>
      )}
    </div>
  )
}

export function SelectCards({
  data,
  updateData,
  errors,
  stepId,
  options,
  columns = 2,
  multiple = false,
  required = false
}: any) {
  const value = data?.[stepId] || (multiple ? [] : '')
  
  const handleSelect = (optionValue: string) => {
    if (multiple) {
      const current = (value || []) as string[]
      const updated = current.includes(optionValue)
        ? current.filter((v: string) => v !== optionValue)
        : [...current, optionValue]
      updateData(stepId, updated)
    } else {
      updateData(stepId, optionValue)
    }
  }

  return (
    <div className="space-y-2">
      <div className={cn(
        "grid gap-3",
        columns === 1 && "grid-cols-1",
        columns === 2 && "grid-cols-1 sm:grid-cols-2",
        columns === 3 && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
      )}>
        {options.map((option: any) => {
          const isSelected = multiple 
            ? value.includes(option.value)
            : value === option.value

          return (
            <button
              key={option.value}
              onClick={() => handleSelect(option.value)}
              className={cn(
                "relative flex items-start gap-3 rounded-lg border p-4",
                "transition-all hover:shadow-md",
                "focus:outline-none focus:ring-2 focus:ring-primary",
                isSelected
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-muted-foreground/50"
              )}
            >
              {option.icon && (
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
                  {option.icon}
                </div>
              )}
              <div className="flex-1 text-left">
                <p className="text-sm font-medium">{option.label}</p>
                {option.description && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {option.description}
                  </p>
                )}
              </div>
              {isSelected && (
                <IconCheck className="h-5 w-5 text-primary absolute top-2 right-2" />
              )}
            </button>
          )
        })}
      </div>
      {errors?.[stepId] && (
        <p className="text-sm text-destructive">{errors[stepId]}</p>
      )}
    </div>
  )
}