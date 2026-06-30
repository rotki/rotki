import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useSessionReady } from './use-session-ready';

const {
  fetchTransactionStatusSummary,
  lastLoginRef,
  navigateToDashboard,
  showGetPremiumButton,
  showReleaseNotesRef,
} = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    fetchTransactionStatusSummary: vi.fn(),
    lastLoginRef: vueRef(''),
    navigateToDashboard: vi.fn(),
    showGetPremiumButton: vi.fn(),
    showReleaseNotesRef: vueRef(true),
  };
});

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
  useAppNavigation: vi.fn(() => ({ navigateToDashboard })),
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
    expect(navigateToDashboard).toHaveBeenCalled();
    expect(get(showReleaseNotesRef)).toBe(false);
  });
});
