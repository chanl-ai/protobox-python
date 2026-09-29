"use client"

import { useState, useCallback, useMemo } from "react"
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Connection,
  EdgeChange,
  NodeChange,
  NodeTypes,
  EdgeTypes,
  Panel,
  Handle,
  Position,
} from "reactflow"
import "reactflow/dist/style.css"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  Plus, 
  Play, 
  Save, 
  Trash2, 
  Settings, 
  Zap, 
  Database, 
  Mail, 
  Clock, 
  AlertCircle,
  CheckCircle,
  ArrowRight,
  Workflow
} from "lucide-react"

// Custom Node Types
const TriggerNode = ({ data }: { data: any }) => (
  <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-3 min-w-[150px]">
    <Handle type="target" position={Position.Top} className="w-3 h-3" />
    <div className="flex items-center gap-2 mb-2">
      <Zap className="h-4 w-4 text-blue-600" />
      <span className="font-medium text-sm">Trigger</span>
    </div>
    <div className="text-xs text-blue-700">{data.label}</div>
    <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
  </div>
)

const ActionNode = ({ data }: { data: any }) => (
  <div className="bg-green-50 border-2 border-green-200 rounded-lg p-3 min-w-[150px]">
    <Handle type="target" position={Position.Top} className="w-3 h-3" />
    <div className="flex items-center gap-2 mb-2">
      <Settings className="h-4 w-4 text-green-600" />
      <span className="font-medium text-sm">Action</span>
    </div>
    <div className="text-xs text-green-700">{data.label}</div>
    <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
  </div>
)

const ConditionNode = ({ data }: { data: any }) => (
  <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-3 min-w-[150px]">
    <Handle type="target" position={Position.Top} className="w-3 h-3" />
    <div className="flex items-center gap-2 mb-2">
      <AlertCircle className="h-4 w-4 text-yellow-600" />
      <span className="font-medium text-sm">Condition</span>
    </div>
    <div className="text-xs text-yellow-700">{data.label}</div>
    <Handle type="source" position={Position.Right} className="w-3 h-3" />
    <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
  </div>
)

const DelayNode = ({ data }: { data: any }) => (
  <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-3 min-w-[150px]">
    <Handle type="target" position={Position.Top} className="w-3 h-3" />
    <div className="flex items-center gap-2 mb-2">
      <Clock className="h-4 w-4 text-purple-600" />
      <span className="font-medium text-sm">Delay</span>
    </div>
    <div className="text-xs text-purple-700">{data.label}</div>
    <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
  </div>
)

const EndNode = ({ data }: { data: any }) => (
  <div className="bg-red-50 border-2 border-red-200 rounded-lg p-3 min-w-[150px]">
    <Handle type="target" position={Position.Top} className="w-3 h-3" />
    <div className="flex items-center gap-2 mb-2">
      <CheckCircle className="h-4 w-4 text-red-600" />
      <span className="font-medium text-sm">End</span>
    </div>
    <div className="text-xs text-red-700">{data.label}</div>
  </div>
)

const nodeTypes: NodeTypes = {
  trigger: TriggerNode,
  action: ActionNode,
  condition: ConditionNode,
  delay: DelayNode,
  end: EndNode,
}

// Node Templates
const nodeTemplates = [
  {
    type: "trigger",
    label: "Schedule Trigger",
    description: "Trigger workflow on a schedule",
    icon: Clock,
    category: "triggers"
  },
  {
    type: "trigger",
    label: "Webhook Trigger",
    description: "Trigger workflow via HTTP webhook",
    icon: Zap,
    category: "triggers"
  },
  {
    type: "action",
    label: "HTTP Request",
    description: "Make HTTP request to external API",
    icon: Database,
    category: "actions"
  },
  {
    type: "action",
    label: "Send Email",
    description: "Send email notification",
    icon: Mail,
    category: "actions"
  },
  {
    type: "action",
    label: "Database Query",
    description: "Execute database query",
    icon: Database,
    category: "actions"
  },
  {
    type: "condition",
    label: "If/Else",
    description: "Conditional logic branching",
    icon: AlertCircle,
    category: "logic"
  },
  {
    type: "delay",
    label: "Wait",
    description: "Wait for specified time",
    icon: Clock,
    category: "timing"
  },
  {
    type: "end",
    label: "End Workflow",
    description: "Terminate workflow execution",
    icon: CheckCircle,
    category: "termination"
  }
]

interface WorkflowEditorProps {
  workflow?: any
  onSave?: (workflow: any) => void
  onTest?: () => void
}

export function WorkflowEditor({ workflow, onSave, onTest }: WorkflowEditorProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [showNodePanel, setShowNodePanel] = useState(false)

  // Initialize with default nodes if empty
  useMemo(() => {
    if (nodes.length === 0 && workflow?.nodes) {
      setNodes(workflow.nodes)
      setEdges(workflow.edges)
    } else if (nodes.length === 0) {
      // Create default start node
      const defaultNodes: Node[] = [
        {
          id: "start",
          type: "trigger",
          position: { x: 250, y: 50 },
          data: { label: "Start Workflow", type: "trigger" },
        },
      ]
      setNodes(defaultNodes)
    }
  }, [workflow, nodes.length, setNodes, setEdges])

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = "move"
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      const type = event.dataTransfer.getData("application/reactflow")
      const label = event.dataTransfer.getData("text/plain")
      
      if (typeof type === "undefined" || !type) {
        return
      }

      const position = {
        x: event.clientX - 250,
        y: event.clientY - 100,
      }

      const newNode: Node = {
        id: `${type}-${Date.now()}`,
        type,
        position,
        data: { label, type },
      }

      setNodes((nds) => nds.concat(newNode))
    },
    [setNodes]
  )

  const addNode = useCallback((template: any) => {
    const newNode: Node = {
      id: `${template.type}-${Date.now()}`,
      type: template.type,
      position: { x: Math.random() * 400, y: Math.random() * 300 },
      data: { label: template.label, type: template.type },
    }
    setNodes((nds) => nds.concat(newNode))
  }, [setNodes])

  const deleteSelectedNode = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((node) => node.id !== selectedNode.id))
      setEdges((eds) => eds.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id))
      setSelectedNode(null)
    }
  }, [selectedNode, setNodes, setEdges])

  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node)
    setShowNodePanel(true)
  }, [])

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave({
        nodes,
        edges,
        metadata: {
          lastModified: new Date().toISOString(),
          nodeCount: nodes.length,
          edgeCount: edges.length,
        }
      })
    }
  }, [nodes, edges, onSave])

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 flex">
        {/* Main Editor */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            fitView
            className="bg-gray-50"
          >
            <Background />
            <Controls />
            <MiniMap />
            
            {/* Floating Node Types Panel */}
            <Panel position="top-left" className="bg-white border rounded-lg p-3 shadow-lg">
              <h4 className="text-sm font-medium mb-3">Workflow Nodes</h4>
              <div className="space-y-2">
                {nodeTemplates.map((template) => (
                  <div
                    key={`${template.type}-${template.label}`}
                    draggable
                    onDragStart={(event) => {
                      event.dataTransfer.setData("application/reactflow", template.type)
                      event.dataTransfer.setData("text/plain", template.label)
                    }}
                    className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-move transition-colors"
                  >
                    <template.icon className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{template.label}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {/* Node Properties Panel */}
        {showNodePanel && selectedNode && (
          <div className="w-80 border-l bg-white p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium">Node Properties</h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowNodePanel(false)}
              >
                ×
              </Button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Node Type</label>
                <div className="mt-1">
                  <Badge variant="outline">
                    {selectedNode.type}
                  </Badge>
                </div>
              </div>
              
              <div>
                <label className="text-sm font-medium">Label</label>
                <input
                  type="text"
                  value={selectedNode.data.label}
                  onChange={(e) => {
                    setNodes((nds) =>
                      nds.map((node) =>
                        node.id === selectedNode.id
                          ? { ...node, data: { ...node.data, label: e.target.value } }
                          : node
                      )
                    )
                  }}
                  className="mt-1 w-full px-3 py-2 border rounded-md text-sm"
                />
              </div>
              
              <div>
                <label className="text-sm font-medium">Position</label>
                <div className="mt-1 text-xs text-muted-foreground">
                  X: {Math.round(selectedNode.position.x)}, Y: {Math.round(selectedNode.position.y)}
                </div>
              </div>
              
              <Separator />
              
              <Button
                variant="destructive"
                size="sm"
                onClick={deleteSelectedNode}
                className="w-full"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Node
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
