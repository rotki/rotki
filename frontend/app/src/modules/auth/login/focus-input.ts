/**
 * Focuses the first non-hidden input rendered inside a field component.
 *
 * Field components wrap their native input, so the caller cannot reach it directly. The
 * parameter is `unknown` rather than `ComponentPublicInstance` because a concrete
 * component instance is not assignable to that generic type (its `$emit` is narrower),
 * and narrowing here keeps every field component usable without a cast.
 *
 * Every step is guarded: a component that renders no input is a no-op.
 *
 * @param component the field component instance whose input should receive focus
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
