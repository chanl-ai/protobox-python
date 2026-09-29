import { redirect } from 'next/navigation'

export default async function PlaygroundPage() {
  // Redirect to the chat page
  redirect('/dashboard/playground/chat')
}