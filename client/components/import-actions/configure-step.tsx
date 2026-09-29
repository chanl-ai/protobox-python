"use client"
import { OpenAPIForm } from "./openapi-form"
import { CurlForm } from "./curl-form"
import type { ImportType } from "./source-selection"

interface ConfigureStepProps {
  importType: ImportType | ""
  openApiForm: {
    specUrl: string
    specContent: string
    baseUrlOverride: string
    includePaths: string
    excludePaths: string
    namePrefix: string
    tags: string
  }
  setOpenApiForm: (updater: (prev: any) => any) => void
  curlForm: {
    curlCommand: string
    name: string
    description: string
    tags: string
  }
  setCurlForm: (updater: (prev: any) => any) => void
  showAdvancedOptions: boolean
  setShowAdvancedOptions: (show: boolean) => void
}

export function ConfigureStep({
  importType,
  openApiForm,
  setOpenApiForm,
  curlForm,
  setCurlForm,
  showAdvancedOptions,
  setShowAdvancedOptions,
}: ConfigureStepProps) {
  return (
    <div className="space-y-4 p-4">
      {importType === "openapi" ? (
        <OpenAPIForm 
          form={openApiForm} 
          setForm={setOpenApiForm}
          showAdvanced={showAdvancedOptions}
          setShowAdvanced={setShowAdvancedOptions}
        />
      ) : importType === "curl" ? (
        <CurlForm 
          form={curlForm} 
          setForm={setCurlForm}
          showAdvanced={showAdvancedOptions}
          setShowAdvanced={setShowAdvancedOptions}
        />
              ) : null}
    </div>
  )
}