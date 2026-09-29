"use client"

import * as React from "react"
import { CalendarDays } from "lucide-react"
import { DateRange } from "react-day-picker"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface DateRangePickerProps {
  value?: DateRange
  onChange?: (range: DateRange | undefined) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function DateRangePicker({
  value,
  onChange,
  placeholder = "Pick a date range",
  className,
  disabled = false,
}: DateRangePickerProps) {
  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  }

  const formatRange = (range?: DateRange) => {
    if (!range?.from) {
      return placeholder
    }

    if (range.to) {
      return `${formatDate(range.from)} - ${formatDate(range.to)}`
    }

    return formatDate(range.from)
  }

  const handleSelect = (range: DateRange | undefined) => {
    onChange?.(range)
  }

  return (
    <div className={cn("grid gap-2", className)}>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant="outline"
            className={cn(
              "w-[280px] justify-start text-left font-normal",
              !value && "text-muted-foreground"
            )}
            disabled={disabled}
          >
            <CalendarDays className="mr-2 h-4 w-4" />
            {formatRange(value)}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            initialFocus
            mode="range"
            defaultMonth={value?.from}
            selected={value}
            onSelect={handleSelect}
            numberOfMonths={2}
            captionLayout="dropdown"
          />
        </PopoverContent>
      </Popover>
    </div>
  )
}

interface DateRangePickerPreset {
  label: string
  value: DateRange | undefined
}

interface DateRangePickerWithPresetsProps extends DateRangePickerProps {
  presets?: DateRangePickerPreset[]
}

export function DateRangePickerWithPresets({
  value,
  onChange,
  presets,
  ...props
}: DateRangePickerWithPresetsProps) {
  const defaultPresets: DateRangePickerPreset[] = [
    {
      label: "Today",
      value: {
        from: new Date(),
        to: new Date(),
      },
    },
    {
      label: "Last 7 days",
      value: {
        from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
        to: new Date(),
      },
    },
    {
      label: "Last 30 days",
      value: {
        from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        to: new Date(),
      },
    },
    {
      label: "Last 90 days",
      value: {
        from: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
        to: new Date(),
      },
    },
  ]

  const presetsToUse = presets || defaultPresets

  return (
    <div className={cn("grid gap-2", props.className)}>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant="outline"
            className={cn(
              "w-[280px] justify-start text-left font-normal",
              !value && "text-muted-foreground"
            )}
            disabled={props.disabled}
          >
            <CalendarDays className="mr-2 h-4 w-4" />
            {value?.from ? (
              value.to ? (
                <>
                  {value.from.toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}{" "}
                  -{" "}
                  {value.to.toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric", 
                    year: "numeric",
                  })}
                </>
              ) : (
                value.from.toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })
              )
            ) : (
              props.placeholder || "Pick a date range"
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <div className="flex">
            <div className="flex flex-col border-r p-3 gap-2">
              <div className="text-sm font-medium text-muted-foreground mb-2">
                Presets
              </div>
              {presetsToUse.map((preset, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  className="justify-start text-sm h-8"
                  onClick={() => onChange?.(preset.value)}
                >
                  {preset.label}
                </Button>
              ))}
            </div>
            <div className="p-0">
              <Calendar
                initialFocus
                mode="range"
                defaultMonth={value?.from}
                selected={value}
                onSelect={onChange}
                numberOfMonths={2}
                captionLayout="dropdown"
              />
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}