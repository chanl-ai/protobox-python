import { redirect } from 'next/navigation'

export default async function PlaygroundPage({
  params,
}: {
  params: Promise<{ workspaceId: string }>
}) {
  const { workspaceId } = await params
  // Redirect to the chat page
  redirect(`/workspace/${workspaceId}/dashboard/playground/chat`)
}