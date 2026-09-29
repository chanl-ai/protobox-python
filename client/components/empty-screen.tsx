"use client"

export function EmptyScreen() {
  return (
    <div className="mx-auto w-full lg:max-w-[70%] px-4 flex-1 flex flex-col justify-center">
      <div className="text-center">
        <div className="text-2xl font-semibold mb-2" style={{ opacity: 1, transform: 'none' }}>
          Hello there!
        </div>
        <div className="text-2xl text-zinc-500" style={{ opacity: 1, transform: 'none' }}>
          How can I help you today?
        </div>
      </div>
    </div>
  )
}