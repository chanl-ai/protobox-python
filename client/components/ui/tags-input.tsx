"use client"

import type React from "react"

import { useState, type KeyboardEvent, useRef, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { X, Check } from "lucide-react"

interface TagsInputProps {
  value?: string[]
  onChange?: (tags: string[]) => void
  placeholder?: string
  className?: string
  suggestions?: string[]
}

export function TagsInput({
  value = [],
  onChange,
  placeholder = "Add tags...",
  className = "",
  suggestions = [],
}: TagsInputProps) {
  const [inputValue, setInputValue] = useState("")
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Filter suggestions based on input and exclude already selected tags
  const filteredSuggestions = suggestions
    .filter(
      (suggestion) =>
        suggestion.toLowerCase().includes(inputValue.toLowerCase()) &&
        !value.includes(suggestion) &&
        inputValue.trim() !== "",
    )
    .slice(0, 5) // Limit to 5 suggestions

  useEffect(() => {
    setShowSuggestions(filteredSuggestions.length > 0 && inputValue.trim() !== "")
    setSelectedIndex(-1)
  }, [inputValue, filteredSuggestions.length])

  const addTag = (tag: string) => {
    const trimmedTag = tag.trim()
    if (trimmedTag && !value.includes(trimmedTag)) {
      const newTags = [...value, trimmedTag]
      onChange?.(newTags)
      setInputValue("")
      setShowSuggestions(false)
      setSelectedIndex(-1)
    }
  }

  const removeTag = (tagToRemove: string) => {
    const newTags = value.filter((tag) => tag !== tagToRemove)
    onChange?.(newTags)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (showSuggestions && filteredSuggestions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault()
        setSelectedIndex((prev) => (prev < filteredSuggestions.length - 1 ? prev + 1 : prev))
      } else if (e.key === "ArrowUp") {
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
      } else if (e.key === "Tab" && selectedIndex >= 0) {
        e.preventDefault()
        addTag(filteredSuggestions[selectedIndex])
      }
    }

    if (e.key === "Enter") {
      e.preventDefault()
      if (selectedIndex >= 0 && filteredSuggestions[selectedIndex]) {
        addTag(filteredSuggestions[selectedIndex])
      } else if (inputValue.trim()) {
        addTag(inputValue)
      }
    } else if (e.key === "Escape") {
      setShowSuggestions(false)
      setSelectedIndex(-1)
    } else if (e.key === "Backspace" && inputValue === "" && value.length > 0) {
      removeTag(value[value.length - 1])
    }
  }

  const handleInputBlur = (e: React.FocusEvent) => {
    // Only hide suggestions if not clicking on a suggestion
    if (!containerRef.current?.contains(e.relatedTarget as Node)) {
      setTimeout(() => {
        setShowSuggestions(false)
        setSelectedIndex(-1)
        if (inputValue.trim()) {
          addTag(inputValue)
        }
      }, 150)
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    addTag(suggestion)
    inputRef.current?.focus()
  }

  return (
    <div className="relative" ref={containerRef}>
      <div
        className={`flex flex-wrap gap-2 p-2 border rounded-md bg-background min-h-[40px] focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 ${className}`}
        onClick={() => inputRef.current?.focus()}
      >
        {value.map((tag) => (
          <Badge key={tag} variant="secondary" className="flex items-center gap-1 px-2 py-1">
            <span>{tag}</span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-auto p-0 w-4 h-4 text-muted-foreground hover:text-foreground ml-1"
              onClick={(e) => {
                e.stopPropagation()
                removeTag(tag)
              }}
            >
              <X className="w-3 h-3" />
            </Button>
          </Badge>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleInputBlur}
          onFocus={() => {
            if (filteredSuggestions.length > 0) {
              setShowSuggestions(true)
            }
          }}
          placeholder={value.length === 0 ? placeholder : ""}
          className="flex-1 min-w-[120px] border-0 outline-none bg-transparent text-sm placeholder:text-muted-foreground"
        />
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <div className="absolute top-full left-0 w-80 mt-1 bg-popover border rounded-md shadow-md z-50 max-h-40 overflow-y-auto">
          {filteredSuggestions.map((suggestion, index) => (
            <button
              key={suggestion}
              type="button"
              className={`w-full text-left px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground flex items-center justify-between ${
                index === selectedIndex ? "bg-accent text-accent-foreground" : ""
              }`}
              onClick={() => handleSuggestionClick(suggestion)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <span>{suggestion}</span>
              {index === selectedIndex && <Check className="w-3 h-3" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}