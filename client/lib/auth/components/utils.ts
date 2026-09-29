// Helper to create button props based on component type
export function getButtonProps(
  Button: React.ComponentType<any> | string,
  props: Record<string, any>
): Record<string, any> {
  if (Button === 'button' || typeof Button === 'string') {
    // Native HTML button - remove custom props
    const { variant, ...htmlProps } = props
    return htmlProps
  }
  // Custom component - pass all props
  return props
}