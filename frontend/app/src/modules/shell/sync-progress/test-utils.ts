/**
 * Shared test utilities for sync-progress module tests.
 * These mocks are hoisted to the top level by vitest.
 *
 * Import this file (or call setupSyncProgressMocks) at the top of test files
 * before other imports.
 */
import { vi } from 'vitest';

vi.mock('@/modules/assets/api/use-asset-icon-api', () => ({
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
