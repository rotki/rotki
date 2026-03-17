/**
 * Shared test utilities for sync-progress module tests.
 * These mocks are hoisted to the top level by vitest.
 *
 * Import this file (or call setupSyncProgressMocks) at the top of test files
 * before other imports.
 */
import { type Mock, vi } from 'vitest';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    assetImageUrl: vi.fn(),
  }),
}));

vi.mock('@/services/websocket/websocket-service');

/**
 * No-op kept for backward compatibility with existing test files.
 * The mocks above are already hoisted and applied at import time.
 */
export function setupSyncProgressMocks(): void {}

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
