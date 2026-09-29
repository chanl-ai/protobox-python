"use client"

import * as React from "react"
import { Bar, BarChart, CartesianGrid, XAxis } from "recharts"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'

interface ExecutionsChartProps {
  data?: Array<{
    date: string
    executions: number
    errors: number
  }>
  title?: string
  description?: string
}

const defaultData = [
  { date: "2024-01-01", executions: 2400, errors: 40 },
  { date: "2024-01-02", executions: 3800, errors: 30 },
  { date: "2024-01-03", executions: 3200, errors: 20 },
  { date: "2024-01-04", executions: 2780, errors: 27 },
  { date: "2024-01-05", executions: 1890, errors: 18 },
  { date: "2024-01-06", executions: 2390, errors: 23 },
  { date: "2024-01-07", executions: 3490, errors: 34 },
]

const chartConfig = {
  views: {
    label: "Actions",
  },
  executions: {
    label: "Executions",
    color: "hsl(var(--chart-1))",
  },
  errors: {
    label: "Errors",
    color: "hsl(var(--chart-2))",
  },
} satisfies ChartConfig

export function ExecutionsChart({ 
  data,
  title = "Executions Overview",
  description = "Action executions over the selected time period"
}: ExecutionsChartProps) {
  const [activeChart, setActiveChart] =
    React.useState<keyof typeof chartConfig>("executions")

  // Check if we have real data or should show empty state
  const hasData = data && data.length > 0 && data.some(d => d.executions > 0 || d.errors > 0)
  const chartData = hasData ? data : []

  const total = React.useMemo(
    () => ({
      executions: chartData.reduce((acc, curr) => acc + curr.executions, 0),
      errors: chartData.reduce((acc, curr) => acc + curr.errors, 0),
    }),
    [chartData]
  )

  // Show empty state if no data
  if (!hasData) {
    return (
      <Card className="overflow-hidden">
        <CardHeader className="flex flex-col items-stretch space-y-0 border-b p-0 sm:flex-row">
          <div className="flex flex-1 flex-col justify-center gap-1 px-6 py-4 sm:py-5">
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="flex flex-col items-center justify-center h-[250px] text-muted-foreground">
            <svg className="h-12 w-12 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p className="text-sm font-medium">No execution data yet</p>
            <p className="text-xs mt-1">Start using actions to see metrics here</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-col items-stretch space-y-0 border-b p-0 sm:flex-row">
        <div className="flex flex-1 flex-col justify-center gap-1 px-6 py-4 sm:py-5">
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        <div className="flex">
          {["executions", "errors"].map((key) => {
            const chart = key as keyof typeof chartConfig
            if (chart === "views") return null
            
            return (
              <button
                key={chart}
                data-active={activeChart === chart}
                className="relative z-30 flex flex-1 flex-col justify-center gap-1 border-t px-6 py-3 text-left even:border-l data-[active=true]:bg-muted/50 sm:border-l sm:border-t-0 sm:px-8 sm:py-4"
                onClick={() => setActiveChart(chart)}
              >
                <span className="text-xs text-muted-foreground">
                  {chartConfig[chart].label}
                </span>
                <span className="text-lg font-bold leading-none sm:text-3xl">
                  {total[key as keyof typeof total].toLocaleString()}
                </span>
              </button>
            )
          })}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ChartContainer
          config={chartConfig}
          className="aspect-auto h-[250px] w-full"
        >
          <BarChart
            accessibilityLayer
            data={data}
            margin={{
              left: 12,
              right: 12,
            }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={32}
              tickFormatter={(value) => {
                const date = new Date(value)
                return date.toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })
              }}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  className="w-[150px]"
                  nameKey="views"
                  labelFormatter={(value) => {
                    return new Date(value).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })
                  }}
                />
              }
            />
            <Bar dataKey={activeChart} fill={`var(--color-${activeChart})`} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}