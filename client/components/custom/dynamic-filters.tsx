"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { X, CirclePlus, Settings2 } from "lucide-react"

export interface FilterOption {
  id: string
  label: string
  count?: number
}

export interface FilterCategory {
  id: string
  label: string
  options: FilterOption[]
}

interface FilterBarProps {
  filterCategories: FilterCategory[]
}

export default function FilterBar({ filterCategories }: FilterBarProps) {
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string[]>>({})

  const handleFilterChange = (categoryId: string, optionId: string, checked: boolean) => {
    setSelectedFilters((prev) => {
      const categoryFilters = prev[categoryId] || []
      if (checked) {
        return {
          ...prev,
          [categoryId]: [...categoryFilters, optionId],
        }
      } else {
        return {
          ...prev,
          [categoryId]: categoryFilters.filter((id) => id !== optionId),
        }
      }
    })
  }

  const removeFilter = (categoryId: string, optionId: string) => {
    handleFilterChange(categoryId, optionId, false)
  }

  const clearAllFilters = () => {
    setSelectedFilters({})
  }

  const getSelectedCount = (categoryId: string) => {
    return selectedFilters[categoryId]?.length || 0
  }

  const getTotalSelectedCount = () => {
    return Object.values(selectedFilters).reduce((total, filters) => total + filters.length, 0)
  }

  const getSelectedFilterLabels = () => {
    const labels: Array<{ categoryId: string; optionId: string; label: string }> = []
    Object.entries(selectedFilters).forEach(([categoryId, optionIds]) => {
      const category = filterCategories.find((cat) => cat.id === categoryId)
      if (category) {
        optionIds.forEach((optionId) => {
          const option = category.options.find((opt) => opt.id === optionId)
          if (option) {
            labels.push({ categoryId, optionId, label: option.label })
          }
        })
      }
    })
    return labels
  }

  return (
    <div className="w-full space-y-4">
      {/* Filter Bar */}
      <div className="flex items-center justify-between">
        <div className="flex flex-1 items-center gap-2">
          <input
            type="text"
            placeholder="Filter tasks..."
            className="file:text-foreground placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground dark:bg-input/30 border-input flex min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive h-8 w-[150px] lg:w-[250px]"
          />

          {filterCategories.map((category) => {
            const selectedCount = getSelectedCount(category.id)
            return (
              <DropdownMenu key={category.id}>
                <DropdownMenuTrigger asChild>
                  <button
                    className={`inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5 h-8 border-dashed ${
                      selectedCount > 0 ? "bg-blue-50 border-blue-200 text-blue-700" : ""
                    }`}
                    type="button"
                    aria-haspopup="dialog"
                    aria-expanded="false"
                    data-state="closed"
                  >
                    <CirclePlus className="lucide lucide-circle-plus" />
                    {category.label}
                    {selectedCount > 0 && (
                      <Badge variant="secondary" className="ml-1 h-4 px-1 text-xs bg-blue-100 text-blue-700">
                        {selectedCount}
                      </Badge>
                    )}
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56 p-2">
                  <div className="space-y-2">
                    <div className="px-2 py-1 text-sm font-medium text-gray-900 border-b">{category.label}</div>
                    {category.options.map((option) => (
                      <div key={option.id} className="flex items-center space-x-2 px-2 py-1 hover:bg-gray-50 rounded">
                        <Checkbox
                          id={`${category.id}-${option.id}`}
                          checked={selectedFilters[category.id]?.includes(option.id) || false}
                          onCheckedChange={(checked) => handleFilterChange(category.id, option.id, checked as boolean)}
                        />
                        <label
                          htmlFor={`${category.id}-${option.id}`}
                          className="flex-1 text-sm cursor-pointer flex items-center justify-between"
                        >
                          <span>{option.label}</span>
                          {option.count && <span className="text-xs text-gray-500">({option.count})</span>}
                        </label>
                      </div>
                    ))}
                  </div>
                </DropdownMenuContent>
              </DropdownMenu>
            )
          })}

          {getTotalSelectedCount() > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="h-8 px-2 text-gray-500 hover:text-gray-700"
            >
              Clear all
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            className="items-center justify-center whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5 ml-auto hidden h-8 lg:flex"
            type="button"
            aria-haspopup="menu"
            aria-expanded="false"
            data-state="closed"
          >
            <Settings2 className="lucide lucide-settings2" />
            View
          </button>
          <button className="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive bg-primary text-primary-foreground shadow-xs hover:bg-primary/90 h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5">
            Add Task
          </button>
        </div>
      </div>

      {/* Active Filters */}
      {getTotalSelectedCount() > 0 && (
        <div className="flex items-center gap-2 px-4">
          <span className="text-sm text-gray-600 font-medium">Active filters:</span>
          <div className="flex items-center gap-2 flex-wrap">
            {getSelectedFilterLabels().map(({ categoryId, optionId, label }) => (
              <Badge
                key={`${categoryId}-${optionId}`}
                variant="secondary"
                className="gap-1 bg-blue-50 text-blue-700 border-blue-200"
              >
                {label}
                <button
                  onClick={() => removeFilter(categoryId, optionId)}
                  className="hover:bg-blue-200 rounded-full p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Sample Content */}
      <div className="p-4 bg-gray-50 rounded-lg">
        <p className="text-sm text-gray-600">
          {getTotalSelectedCount() > 0
            ? `Showing results with ${getTotalSelectedCount()} active filter${getTotalSelectedCount() > 1 ? "s" : ""}`
            : "Showing all results"}
        </p>
      </div>
    </div>
  )
}
