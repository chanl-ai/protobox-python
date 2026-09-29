"use client"

import { useState } from "react"
import { Column } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { X, Search, Filter } from "lucide-react"
import { Prompt } from "./columns"

interface DataTableToolbarProps {
  table: any
}

export function DataTableToolbar({ table }: DataTableToolbarProps) {
  const [searchValue, setSearchValue] = useState("")
  const [categoryFilter, setCategoryFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("all")

  // Get unique categories and statuses for filter options
  const categories = Array.from(
    new Set(
      table.getCoreRowModel().rows.map((row: any) => row.original.category)
    )
  )

  const statuses = Array.from(
    new Set(
      table.getCoreRowModel().rows.map((row: any) => row.original.status)
    )
  )

  // Apply filters
  const applyFilters = () => {
    const columnFilters = []
    
    if (searchValue) {
      columnFilters.push({
        id: "name",
        value: searchValue,
      })
    }
    
    if (categoryFilter !== "all") {
      columnFilters.push({
        id: "category", 
        value: categoryFilter,
      })
    }
    
    if (statusFilter !== "all") {
      columnFilters.push({
        id: "status",
        value: statusFilter,
      })
    }
    
    table.setColumnFilters(columnFilters)
  }

  // Clear all filters
  const clearFilters = () => {
    setSearchValue("")
    setCategoryFilter("all")
    setStatusFilter("all")
    table.setColumnFilters([])
  }

  // Check if any filters are active
  const isFiltered = searchValue || categoryFilter !== "all" || statusFilter !== "all"

  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-1 items-center space-x-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search prompts..."
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                applyFilters()
              }
            }}
            className="pl-8"
          />
        </div>
        
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map((category) => (
              <SelectItem key={category} value={category}>
                {category}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            {statuses.map((status) => (
              <SelectItem key={status} value={status}>
                {status}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="sm"
          onClick={applyFilters}
          className="h-9"
        >
          <Filter className="mr-2 h-4 w-4" />
          Apply
        </Button>

        {isFiltered && (
          <Button
            variant="ghost"
            onClick={clearFilters}
            className="h-9 px-2 lg:px-3"
          >
            Reset
            <X className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Active filters display */}
      {isFiltered && (
        <div className="flex items-center space-x-2">
          <span className="text-sm text-muted-foreground">Active filters:</span>
          {searchValue && (
            <Badge variant="secondary" className="gap-1">
              Search: {searchValue}
              <X 
                className="h-3 w-3 cursor-pointer" 
                onClick={() => {
                  setSearchValue("")
                  applyFilters()
                }}
              />
            </Badge>
          )}
          {categoryFilter !== "all" && (
            <Badge variant="secondary" className="gap-1">
              Category: {categoryFilter}
              <X 
                className="h-3 w-3 cursor-pointer" 
                onClick={() => {
                  setCategoryFilter("all")
                  applyFilters()
                }}
              />
            </Badge>
          )}
          {statusFilter !== "all" && (
            <Badge variant="secondary" className="gap-1">
              Status: {statusFilter}
              <X 
                className="h-3 w-3 cursor-pointer" 
                onClick={() => {
                  setStatusFilter("all")
                  applyFilters()
                }}
              />
            </Badge>
          )}
        </div>
      )}
    </div>
  )
}
