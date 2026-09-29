"use client"

import { ChevronRight } from "lucide-react"

export type ImportStep = "source" | "configure" | "preview" | "result"

interface ProgressIndicatorProps {
  currentStep: ImportStep
}

export function ProgressIndicator({ currentStep }: ProgressIndicatorProps) {
  const getStepState = (step: ImportStep) => {
    const steps = ["source", "configure", "preview", "result"]
    const currentIndex = steps.indexOf(currentStep)
    const stepIndex = steps.indexOf(step)
    
    if (stepIndex < currentIndex) return "completed"
    if (stepIndex === currentIndex) return "current"
    return "upcoming"
  }

  const getStepClasses = (step: ImportStep) => {
    const state = getStepState(step)
    if (state === "completed" || state === "current") {
      return "border-primary bg-primary text-primary-foreground"
    }
    return "border-muted-foreground"
  }

  return (
    <div className="flex items-center space-x-1.5">
      <div className={`flex items-center space-x-1.5 ${currentStep === "source" ? "text-primary" : "text-muted-foreground"}`}>
        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-medium ${getStepClasses("source")}`}>
          1
        </div>
        <span className="text-xs font-medium">Source</span>
      </div>
      <ChevronRight className="w-3 h-3 text-muted-foreground" />
      <div className={`flex items-center space-x-1.5 ${currentStep === "configure" ? "text-primary" : "text-muted-foreground"}`}>
        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-medium ${getStepClasses("configure")}`}>
          2
        </div>
        <span className="text-xs font-medium">Configure</span>
      </div>
      <ChevronRight className="w-3 h-3 text-muted-foreground" />
      <div className={`flex items-center space-x-1.5 ${currentStep === "preview" ? "text-primary" : "text-muted-foreground"}`}>
        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-medium ${getStepClasses("preview")}`}>
          3
        </div>
        <span className="text-xs font-medium">Preview</span>
      </div>
      <ChevronRight className="w-3 h-3 text-muted-foreground" />
      <div className={`flex items-center space-x-1.5 ${currentStep === "result" ? "text-primary" : "text-muted-foreground"}`}>
        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-medium ${getStepClasses("result")}`}>
          4
        </div>
        <span className="text-xs font-medium">Result</span>
      </div>
    </div>
  )
}
