/**
 * Focuses the first non-hidden input rendered inside a field component.
 *
 * @remarks
 * Field components wrap their native input, so the caller cannot reach it directly. Every step is
 * guarded, and a component rendering no input is a no-op.
 *
 * The parameter is `unknown`, not `ComponentPublicInstance`: a concrete component instance is not
 * assignable to that generic type, since its `$emit` is narrower. Narrowing here keeps every field
 * component usable without a cast.
 *
 * @param component - the field component instance whose input should receive focus
 */
export function focusInput(component: unknown): void {
  if (typeof component !== 'object' || component === null || !('$el' in component))
    return;

  const root = component.$el;

  if (!(root instanceof Element))
    return;

  const input = root.querySelector('input:not([type=hidden])');

  if (input instanceof HTMLInputElement)
    input.focus();
}
