"use client"

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { SlugInput } from "@/components/ui/slug-input"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Save, Trash2, AlertTriangle } from "lucide-react"
import { toast } from "@/lib/toast"
import { useAuth } from "@/lib/auth"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { protoboxClient } from "@/lib/api/protobox-client"
import { useRouter } from "next/navigation"

const workspaceFormSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(100, "Name must be less than 100 characters"),
  description: z.string().max(500, "Description must be less than 500 characters").optional(),
  slug: z.string().min(3, "Slug must be at least 3 characters").max(63, "Slug must be less than 63 characters")
    .regex(/^[a-z0-9-]+$/, "Slug can only contain lowercase letters, numbers, and hyphens")
    .optional(),
})

type WorkspaceFormValues = z.infer<typeof workspaceFormSchema>

export default function GeneralSettingsPage() {
  const router = useRouter()
  const { currentWorkspace, refreshWorkspaces: refreshAuthWorkspaces } = useAuth()
  const { refreshWorkspaces: refreshProviderWorkspaces } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [puzzleAnswer, setPuzzleAnswer] = useState("")
  const [expectedAnswer] = useState(() => {
    // Simple math puzzle
    const a = Math.floor(Math.random() * 10) + 1
    const b = Math.floor(Math.random() * 10) + 1
    return { question: `${a} + ${b}`, answer: (a + b).toString() }
  })

  const form = useForm<WorkspaceFormValues>({
    resolver: zodResolver(workspaceFormSchema),
    defaultValues: {
      name: "",
      description: "",
      slug: "",
    },
  })

  // Load workspace data when component mounts or workspace changes
  useEffect(() => {
    if (currentWorkspace) {
      form.reset({
        name: currentWorkspace.name || "",
        description: currentWorkspace.description || "",
        slug: currentWorkspace.slug || "",
      })
    }
  }, [currentWorkspace, form])

  const onSubmit = async (data: WorkspaceFormValues) => {
    // WorkspaceLoadingGuard guarantees currentWorkspace exists

    setLoading(true)
    try {
      const updateData = {
        name: data.name,
        description: data.description,
        slug: data.slug,
      }
      
      
      const result = await protoboxClient.updateWorkspace(currentWorkspace!._id, updateData)
      
      
      // Refresh both auth store and workspace provider to update the UI everywhere
      await Promise.all([
        refreshAuthWorkspaces(),
        refreshProviderWorkspaces()
      ])
      
      // Show success toast in the center of the screen
      toast.success("Workspace settings updated successfully", { centered: true })
      
      // Reset form with new values to clear dirty state
      if (result) {
        form.reset({
          name: result.name || data.name,
          description: result.description || data.description,
          slug: result.slug || data.slug,
        })
      }
    } catch (error) {
      toast.error("Failed to update workspace settings")
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteClick = () => {
    setPuzzleAnswer("")
    setDeleteDialogOpen(true)
  }

  const handlePuzzleSubmit = () => {
    if (puzzleAnswer === expectedAnswer.answer) {
      setDeleteDialogOpen(false)
      setDeleteConfirmOpen(true)
    } else {
      toast.error("Please solve the puzzle correctly to continue")
    }
  }

  const handleDeleteWorkspace = async () => {
    // WorkspaceLoadingGuard guarantees currentWorkspace exists

    setLoading(true)
    try {
      await protoboxClient.deleteWorkspace(currentWorkspace!._id)
      
      // Refresh both stores after deletion
      await Promise.all([
        refreshAuthWorkspaces(),
        refreshProviderWorkspaces()
      ])
      
      toast.success("Workspace deleted successfully", { centered: true })
      
      // Redirect to dashboard or onboarding
      router.push("/dashboard")
    } catch (error) {
      toast.error("Failed to delete workspace")
    } finally {
      setLoading(false)
      setDeleteConfirmOpen(false)
    }
  }

  // WorkspaceLoadingGuard guarantees currentWorkspace exists - no need to check

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Workspace Settings</CardTitle>
            <CardDescription>
              Manage your workspace information and preferences
            </CardDescription>
          </div>
          <Button 
            onClick={form.handleSubmit(onSubmit)} 
            disabled={loading || !form.formState.isDirty}
          >
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form className="space-y-6">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Workspace Name</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="My Workspace" />
                    </FormControl>
                    <FormDescription>
                      The display name for your workspace.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="slug"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <SlugInput
                        value={field.value || ""}
                        onChange={field.onChange}
                        workspaceId={currentWorkspace!._id}
                        workspaceName={form.watch("name")}
                        disabled={loading}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        className="resize-none"
                        rows={4}
                        placeholder="Describe your workspace..."
                      />
                    </FormControl>
                    <FormDescription>
                      Optional description of what this workspace is used for.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="pt-4">
                <div className="text-sm text-muted-foreground">
                  <p>Workspace ID: {currentWorkspace!._id}</p>
                  <p>Created: {new Date(currentWorkspace!.created_at).toLocaleDateString()}</p>
                  <p>Last Updated: {new Date(currentWorkspace!.updated_at).toLocaleDateString()}</p>
                </div>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      {/* Delete Workspace Section */}
      <Card className="mt-6 border-destructive/50">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>
            Irreversible and destructive actions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-destructive/50 p-4">
              <div>
                <h4 className="font-medium">Delete Workspace</h4>
                <p className="text-sm text-muted-foreground">
                  Once you delete a workspace, there is no going back. All data will be permanently removed.
                </p>
              </div>
              <Button 
                variant="destructive" 
                onClick={handleDeleteClick}
                disabled={loading}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Workspace
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Puzzle Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              To confirm you want to delete this workspace, please solve this simple puzzle:
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="text-center">
              <p className="text-2xl font-mono mb-4">
                What is {expectedAnswer.question}?
              </p>
              <Input
                type="text"
                placeholder="Enter your answer"
                value={puzzleAnswer}
                onChange={(e) => setPuzzleAnswer(e.target.value)}
                className="max-w-[200px] mx-auto"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handlePuzzleSubmit()
                  }
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handlePuzzleSubmit}>
              Verify & Continue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Final Confirmation Dialog */}
      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Are you absolutely sure?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the workspace
              <span className="font-semibold"> {currentWorkspace!.name}</span>
              and remove all associated data including actions, secrets, and executions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteWorkspace}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete Workspace
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}