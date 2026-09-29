export default function ExamplePage() {
  return (
    <div className="space-y-6">
      <div className="px-4 lg:px-6">
        <h1 className="text-2xl font-bold">Example Dashboard Page</h1>
        <p className="text-muted-foreground">
          This is an example page that uses the dashboard layout.
        </p>
      </div>
      
      <div className="px-4 lg:px-6">
        <div className="rounded-lg border bg-card p-6">
          <h2 className="text-lg font-semibold mb-4">Custom Content</h2>
          <p className="text-sm text-muted-foreground">
            Any content you place here will be rendered between the 
            "Content starts here" and "Content ends here" comments in the layout.
          </p>
        </div>
      </div>
      
      <div className="px-4 lg:px-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium">Card 1</h3>
            <p className="text-sm text-muted-foreground">Sample content</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium">Card 2</h3>
            <p className="text-sm text-muted-foreground">Sample content</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <h3 className="font-medium">Card 3</h3>
            <p className="text-sm text-muted-foreground">Sample content</p>
          </div>
        </div>
      </div>
    </div>
  )
} 