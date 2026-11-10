import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceDisplayModeStore } from './use-balance-display-mode-store';

describe('useBalanceDisplayModeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.unstubAllEnvs();
  });

  it('should enter history mode when the accounting update is enabled', () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', 'true');
    const store = useBalanceDisplayModeStore();
    store.setMode('history');

    expect(store.isHistoryMode).toBe(true);
  });

  it('should stay queried when the accounting update is disabled', () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', '');
    const store = useBalanceDisplayModeStore();
    store.setMode('history');

    expect(store.mode).toBe('queried');
    expect(store.isHistoryMode).toBe(false);
  });

  it('should never report history mode when disabled, even if the state is set directly', () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', '');
    const store = useBalanceDisplayModeStore();
    store.mode = 'history';

    expect(store.isHistoryMode).toBe(false);
  });
});
