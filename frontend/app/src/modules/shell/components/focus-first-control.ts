const FOCUSABLE = 'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Focuses the first enabled control inside `container`, such as the trigger a question was asked
 * from once it is answered.
 *
 * @remarks
 * Does nothing when the container is gone or holds nothing focusable, for example a trigger the
 * answer removed or disabled.
 */
export function focusFirstControl(container: HTMLElement | null | undefined): void {
  container?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
}
