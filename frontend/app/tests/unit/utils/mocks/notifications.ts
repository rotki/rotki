import { type Mock, vi } from 'vitest';

export interface NotificationSpies {
  notify?: Mock;
  notifyError?: Mock;
  notifyWarning?: Mock;
  notifyInfo?: Mock;
  removeMatching?: Mock;
  showSuccessMessage?: Mock;
  showErrorMessage?: Mock;
}

/**
 * Builds the `useNotifications` mock used by ~48 specs. Pass only the spies the
 * test asserts on; the rest default to harmless `vi.fn()` stubs so unrelated
 * calls (e.g. an incidental `notifyInfo`) don't blow up.
 *
 * Declare the spies with `vi.hoisted` so they exist before the `vi.mock`
 * factory reads them:
 *
 * ```ts
 * const { notifyError } = vi.hoisted(() => ({ notifyError: vi.fn() }));
 * vi.mock('@/modules/core/notifications/use-notifications', () =>
 *   mockUseNotifications({ notifyError }),
 * );
 * ```
 */
export function mockUseNotifications(spies: NotificationSpies = {}): { useNotifications: Mock } {
  const resolved = {
    notify: spies.notify ?? vi.fn(),
    notifyError: spies.notifyError ?? vi.fn(),
    notifyWarning: spies.notifyWarning ?? vi.fn(),
    notifyInfo: spies.notifyInfo ?? vi.fn(),
    removeMatching: spies.removeMatching ?? vi.fn(),
    showSuccessMessage: spies.showSuccessMessage ?? vi.fn(),
    showErrorMessage: spies.showErrorMessage ?? vi.fn(),
  };

  return {
    useNotifications: vi.fn(() => resolved),
  };
}
