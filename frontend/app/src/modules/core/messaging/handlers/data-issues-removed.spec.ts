import { get } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { createDataIssuesRemovedHandler } from './data-issues-removed';

const { mockRefreshSummary } = vi.hoisted(() => ({
  mockRefreshSummary: vi.fn<() => Promise<void>>(),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: vi.fn(() => ({ refreshSummary: mockRefreshSummary })),
}));

describe('modules/core/messaging/handlers/data-issues-removed', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockRefreshSummary.mockResolvedValue(undefined);
  });

  it('should notify the inbox store and refresh the summary when no reload listener is active', async () => {
    const store = useDataIssuesInboxStore();
    const handler = createDataIssuesRemovedHandler();

    const result = await handler.handle({ assets: ['eip155:1/erc20:0x1111'] });

    expect(result).toBeUndefined();
    expect(get(store.issuesInvalidated)).toBe(1);
    expect(get(store.lastRemovedAssets)).toStrictEqual(['eip155:1/erc20:0x1111']);
    expect(mockRefreshSummary).toHaveBeenCalledOnce();
  });

  it('should notify the inbox store without refreshing the summary directly when an active reload listener exists', async () => {
    const store = useDataIssuesInboxStore();
    store.incrementReloadListeners();
    const handler = createDataIssuesRemovedHandler();

    await handler.handle({ assets: ['eip155:1/erc20:0x2222'] });

    expect(get(store.issuesInvalidated)).toBe(1);
    expect(get(store.lastRemovedAssets)).toStrictEqual(['eip155:1/erc20:0x2222']);
    expect(mockRefreshSummary).not.toHaveBeenCalled();
  });
});
