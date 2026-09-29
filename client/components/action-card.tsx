import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { 
  Play, 
  MoreHorizontal, 
  Edit, 
  Settings, 
  Trash2, 
  Globe, 
  Database, 
  Code, 
  Bot,
  Activity,
  Clock
} from "lucide-react"

export interface Action {
  id: string
  name: string
  type: "REST" | "DATABASE" | "CODE_RUN" | "O3"
  status: "active" | "inactive"
  lastExecuted: string
  executions: number
  description?: string
}

interface ActionCardProps {
  action: Action
  onEdit?: (action: Action) => void
  onDelete?: (action: Action) => void
  onExecute?: (action: Action) => void
  onSettings?: (action: Action) => void
}

const typeIcons = {
  REST: Globe,
  DATABASE: Database,
  CODE_RUN: Code,
  O3: Bot,
}

const typeColors = {
  REST: "bg-blue-500",
  DATABASE: "bg-green-500",
  CODE_RUN: "bg-orange-500",
  O3: "bg-purple-500",
}

export function ActionCard({ 
  action, 
  onEdit, 
  onDelete, 
  onExecute, 
  onSettings 
}: ActionCardProps) {
  const Icon = typeIcons[action.type]
  
  return (
    <Card className="group relative hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${typeColors[action.type]} text-white`}>
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <CardTitle className="text-base font-semibold line-clamp-1">
              {action.name}
            </CardTitle>
            <div className="flex items-center space-x-2 mt-1">
              <Badge variant="secondary" className="text-xs">
                {action.type}
              </Badge>
              <Badge 
                variant={action.status === "active" ? "default" : "destructive"}
                className="text-xs"
              >
                {action.status === "active" ? "Live" : "Inactive"}
              </Badge>
            </div>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreHorizontal className="h-4 w-4" />
              <span className="sr-only">Open menu</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={() => onExecute?.(action)}>
              <Play className="mr-2 h-4 w-4" />
              Execute
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onEdit?.(action)}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onSettings?.(action)}>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={() => onDelete?.(action)}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>
      
      <CardContent className="pb-2">
        {action.description && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
            {action.description}
          </p>
        )}
        
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center space-x-2">
            <Activity className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">Executions</span>
          </div>
          <div className="font-medium text-right">
            {action.executions}
          </div>
          
          <div className="flex items-center space-x-2">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">Last run</span>
          </div>
          <div className="font-medium text-right text-sm">
            {action.lastExecuted}
          </div>
        </div>
      </CardContent>
      
      <CardFooter className="pt-2">
        <Button 
          size="sm" 
          className="w-full" 
          onClick={() => onExecute?.(action)}
          disabled={action.status === "inactive"}
        >
          <Play className="mr-2 h-3 w-3" />
          Execute
        </Button>
      </CardFooter>
    </Card>
  )
} 