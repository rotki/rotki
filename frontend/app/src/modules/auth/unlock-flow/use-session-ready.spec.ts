import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useSessionReady } from './use-session-ready';

const {
  fetchTransactionStatusSummary,
  lastLoginRef,
  navigateAfterUnlock,
  refreshSupportedChains,
  showGetPremiumButton,
  showReleaseNotesRef,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    fetchTransactionStatusSummary: vi.fn(),
    lastLoginRef: ref<string>(''),
    navigateAfterUnlock: vi.fn(),
    refreshSupportedChains: vi.fn(),
    showGetPremiumButton: vi.fn(),
    showReleaseNotesRef: ref<boolean>(true),
  };
});

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ refreshSupportedChains })),
}));

vi.mock('@/modules/auth/account-management', () => ({
  lastLogin: lastLoginRef,
}));

vi.mock('@/modules/premium/use-premium-helper', () => ({
  usePremiumHelper: vi.fn(() => ({ showGetPremiumButton })),
}));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: vi.fn(() => ({ fetchTransactionStatusSummary })),
}));

vi.mock('@/modules/shell/layout/use-navigation', () => ({
  useAppNavigation: vi.fn(() => ({ navigateAfterUnlock })),
}));

vi.mock('@/modules/core/messaging/use-update-message', () => ({
  useUpdateMessage: vi.fn(() => ({ showReleaseNotes: showReleaseNotesRef })),
}));

describe('useSessionReady', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(lastLoginRef, '');
    set(showReleaseNotesRef, true);
  });

  it('should run the shared post-unlock side-effects', async () => {
    const authStore = useSessionAuthStore();
    const { canRequestData, username } = storeToRefs(authStore);
    set(username, 'alice');

    await useSessionReady().handleSessionReady();

    expect(get(canRequestData)).toBe(true);
    expect(get(lastLoginRef)).toBe('alice');
    expect(showGetPremiumButton).toHaveBeenCalled();
    expect(fetchTransactionStatusSummary).toHaveBeenCalled();
    expect(navigateAfterUnlock).toHaveBeenCalled();
    expect(get(showReleaseNotesRef)).toBe(false);
  });

  it('should load the supported chains before navigating to the first page', async () => {
    await useSessionReady().handleSessionReady();

    expect(refreshSupportedChains).toHaveBeenCalledOnce();
    // chains must be populated before the first page (and its consumers) mount
    expect(refreshSupportedChains.mock.invocationCallOrder[0])
      .toBeLessThan(navigateAfterUnlock.mock.invocationCallOrder[0]);
  });
});
