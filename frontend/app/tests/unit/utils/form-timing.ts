import { vi } from 'vitest';

const FORM_DEBOUNCE_MS = 600;

/**
 * Advances fake timers past the window a form's debounced watchers need to become observable.
 *
 * @remarks
 * Seeding a form from its `data` prop and reacting to a user's edit both run behind the same
 * debounce, so a test that does not cross this window sees neither. Call it after mounting to
 * settle the seeding before an edit, and again after the edit to observe what the edit did.
 * Requires `vi.useFakeTimers()`.
 */
export async function settleFormDebounce(): Promise<void> {
  await vi.advanceTimersByTimeAsync(FORM_DEBOUNCE_MS);
}
