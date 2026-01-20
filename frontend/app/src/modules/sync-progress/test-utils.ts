/**
 * Shared test utilities for sync-progress module tests.
 * These helpers reduce boilerplate in component and composable tests.
 */
import { type Mock, vi } from 'vitest';

/**
 * Sets up common mocks used across sync-progress component tests.
 * Call this at the top of test files before other imports.
 *
 * @example
 * ```ts
 * import { setupSyncProgressMocks } from '../test-utils';
 *
 * setupSyncProgressMocks();
 *
 * // Rest of your test file...
 * ```
 */
export function setupSyncProgressMocks(): void {
  vi.mock('@/composables/api/assets/icon', () => ({
    useAssetIconApi: vi.fn().mockReturnValue({
      assetImageUrl: vi.fn(),
    }),
  }));

  vi.mock('@/services/websocket/websocket-service');
}

/**
 * Creates a hoisted mock function with a default return value.
 * Use this with vi.hoisted() for mocks that need to be available before module imports.
 *
 * @param returnValue - The value the mock should return
 * @returns A mock function configured with the return value
 */
export function createHoistedMock<T>(returnValue: T): Mock<() => T> {
  return vi.fn().mockReturnValue(returnValue);
}
