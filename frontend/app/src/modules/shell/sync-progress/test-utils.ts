/**
 * Shared test utilities for sync-progress module tests.
 * These mocks are hoisted to the top level by vitest.
 *
 * Import this file (or call setupSyncProgressMocks) at the top of test files
 * before other imports.
 */
import type { DOMWrapper } from '@vue/test-utils';
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

/**
 * Whether a progress row is rendered in its compact form.
 *
 * @remarks
 * The list stubs render `compact` through `String(compact === true)`, so the attribute is a
 * stringified boolean rather than a present-or-absent flag.
 */
export function isCompact(item: DOMWrapper<Element> | undefined): boolean {
  return item?.attributes('data-compact') === 'true';
}
