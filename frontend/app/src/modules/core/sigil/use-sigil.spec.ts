import type { EffectScope } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { SigilEventMap, SigilQueueEntry } from '@/modules/core/sigil/types';
import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { sigilBus } from '@/modules/core/sigil/event-bus';

const mockEnqueue = vi.fn<(entry: Omit<SigilQueueEntry, 'id'>) => Promise<void>>().mockResolvedValue(undefined);
const mockStartQueue = vi.fn();
const mockStopQueue = vi.fn();

vi.mock('@/modules/core/sigil/use-sigil-queue', () => ({
  WEBSITE_ID: 'test-website-id',
  enqueue: async (entry: Omit<SigilQueueEntry, 'id'>): Promise<void> => mockEnqueue(entry),
  startQueue: (): void => mockStartQueue(),
  stopQueue: (): void => mockStopQueue(),
}));

const mockSessionConfig: SigilEventMap['session_config'] = {
  premium: false,
  plan: 'Free',
  appVersion: '1.0',
  mainCurrency: 'USD',
  language: 'en',
  theme: 'auto',
  appMode: 'web',
  priceOracles: '',
};

const mockExchangesSummary: SigilEventMap['exchanges_summary'] = { premium: false, plan: 'Free', exchangeCount: 0 };
const mockBalancesSummary: SigilEventMap['balances_summary'] = { premium: false, plan: 'Free', hasManualBalances: false, distinctAssetCount: 0, totalAccounts: 0, totalChains: 0 };
const mockHistorySync: SigilEventMap['history_sync'] = { premium: false, plan: 'Free', totalEvents: 10, spamEvents: 2, totalGroups: 5 };

vi.mock('@/modules/core/sigil/handlers/session-config', () => ({
  useSessionConfigHandler: vi.fn(() => (): SigilEventMap['session_config'] => ({ ...mockSessionConfig })),
}));

vi.mock('@/modules/core/sigil/handlers/exchanges-summary', () => ({
  useExchangesSummaryHandler: vi.fn(() => (): SigilEventMap['exchanges_summary'] => ({ ...mockExchangesSummary })),
}));

vi.mock('@/modules/core/sigil/handlers/balances-summary', () => ({
  useBalancesSummaryHandler: vi.fn(() => (): SigilEventMap['balances_summary'] => ({ ...mockBalancesSummary })),
}));

vi.mock('@/modules/core/sigil/handlers/history-sync', () => ({
  useHistorySyncHandler: vi.fn(() => async (): Promise<SigilEventMap['history_sync']> => Promise.resolve({ ...mockHistorySync })),
}));

const mockLogged = ref<boolean>(false);
const mockSubmitUsageAnalytics = ref<boolean>(false);
const mockIsDevelop = ref<boolean>(false);

const mockUsername = ref<string>('bob');

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: vi.fn(() => ({
    $id: 'session/auth',
    logged: mockLogged,
    username: mockUsername,
  })),
}));

const mockClientId = ref<string>('');

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'clientId' ? mockClientId : mockSubmitUsageAnalytics)),
}));

const mockUpdateFrontendSetting = vi
  .fn<(payload: FrontendSettingsPayload) => Promise<ActionStatus>>()
  .mockResolvedValue({ success: true });

vi.mock('@/modules/settings/use-frontend-settings-writer', () => ({
  useFrontendSettingsWriter: vi.fn(() => ({
    updateFrontendSetting: async (payload: FrontendSettingsPayload): Promise<ActionStatus> =>
      mockUpdateFrontendSetting(payload),
  })),
}));

const mockCacheClientId = vi.fn<(username: string, id: string) => void>();
const mockReadCachedClientId = vi.fn<(username: string) => string | undefined>();

const mockSetCurrentClientId = vi.fn<(id: string) => void>();
const mockClearCurrentClientId = vi.fn();

vi.mock('@/modules/core/sigil/use-sigil-identity', () => ({
  cacheClientId: (username: string, id: string): void => mockCacheClientId(username, id),
  clearCurrentClientId: (): void => mockClearCurrentClientId(),
  createClientId: (): string => 'minted-id',
  getInstanceId: (): string => 'instance-1',
  readCachedClientId: (username: string): string | undefined => mockReadCachedClientId(username),
  setCurrentClientId: (id: string): void => mockSetCurrentClientId(id),
}));

/** The identify entries the composable queued, in order. */
function identifyEntries(): Omit<SigilQueueEntry, 'id'>[] {
  return mockEnqueue.mock.calls.map(call => call[0]).filter(entry => entry.kind === 'identify');
}

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: vi.fn(() => ({
    $id: 'main',
    isDevelop: mockIsDevelop,
  })),
}));

const mockCapabilities = ref<Record<string, unknown> | undefined>({ currentTier: 'Free' });

vi.mock('@/modules/premium/use-premium-store', () => ({
  usePremiumStore: vi.fn(() => ({
    $id: 'session/premium',
    capabilities: mockCapabilities,
  })),
}));

let afterEachCallback: ((to: any) => void) | undefined;
const mockRemoveHook = vi.fn();

vi.mock('@/router', () => ({
  router: {
    currentRoute: { value: { path: '/dashboard', params: {}, matched: [{ path: '/dashboard' }] } },
    afterEach: vi.fn((cb: (to: any) => void) => {
      afterEachCallback = cb;
      return mockRemoveHook;
    }),
  },
}));

const { useSigil } = await import('@/modules/core/sigil/use-sigil');

function activateSigil(): void {
  set(mockLogged, true);
  set(mockSubmitUsageAnalytics, true);
  set(mockIsDevelop, false);
}

describe('useSigil', () => {
  let scope: EffectScope;

  beforeEach(() => {
    scope = effectScope();
    mockEnqueue.mockClear();
    mockStartQueue.mockClear();
    mockStopQueue.mockClear();
    mockRemoveHook.mockClear();
    mockUpdateFrontendSetting.mockClear();
    mockUpdateFrontendSetting.mockResolvedValue({ success: true });
    mockCacheClientId.mockClear();
    mockReadCachedClientId.mockReset();
    mockSetCurrentClientId.mockClear();
    mockClearCurrentClientId.mockClear();
    set(mockClientId, '');
    set(mockUsername, 'bob');
    set(mockLogged, false);
    set(mockSubmitUsageAnalytics, false);
    set(mockIsDevelop, false);
    set(mockCapabilities, { currentTier: 'Free' });
    afterEachCallback = undefined;
    sigilBus.all.clear();
  });

  afterEach(() => {
    scope.stop();
  });

  describe('shared instance', () => {
    it('should return the same instance across multiple calls while active', () => {
      activateSigil();
      const instance1 = scope.run(() => useSigil());
      const instance2 = scope.run(() => useSigil());
      expect(instance1).toBe(instance2);
    });
  });

  describe('activation gate', () => {
    it('should not activate when not logged in', async () => {
      scope.run(() => useSigil());
      await nextTick();
      expect(mockStartQueue).not.toHaveBeenCalled();
    });

    it('should not activate when analytics disabled', async () => {
      set(mockLogged, true);
      set(mockSubmitUsageAnalytics, false);

      scope.run(() => useSigil());
      await nextTick();
      expect(mockStartQueue).not.toHaveBeenCalled();
    });

    it('should not activate in dev mode without debug flag', async () => {
      set(mockLogged, true);
      set(mockSubmitUsageAnalytics, true);
      set(mockIsDevelop, true);

      scope.run(() => useSigil());
      await nextTick();
      expect(mockStartQueue).not.toHaveBeenCalled();
    });

    it('should activate when all conditions met', async () => {
      activateSigil();

      scope.run(() => useSigil());
      await nextTick();
      expect(mockStartQueue).toHaveBeenCalledOnce();
    });
  });

  describe('deactivation', () => {
    it('should deactivate when user logs out', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      set(mockLogged, false);
      await nextTick();

      expect(mockStopQueue).toHaveBeenCalled();
    });

    it('should deactivate when analytics toggled off', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      set(mockSubmitUsageAnalytics, false);
      await nextTick();

      expect(mockStopQueue).toHaveBeenCalled();
    });

    it('should unregister router hook on deactivate', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      set(mockLogged, false);
      await nextTick();

      expect(mockRemoveHook).toHaveBeenCalled();
    });
  });

  describe('client id', () => {
    it('should adopt the stored value without writing', async () => {
      set(mockClientId, 'existing-id');
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(identifyEntries()).toHaveLength(1);
      expect(identifyEntries()[0].clientId).toBe('existing-id');
      expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
    });

    it('should mint and persist one when neither the settings nor the cache have one', async () => {
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ clientId: 'minted-id' });
      expect(identifyEntries()[0].clientId).toBe('minted-id');
    });

    it('should recover the cached value rather than mint when the settings lost it', async () => {
      mockReadCachedClientId.mockReturnValue('earlier-id');
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(mockReadCachedClientId).toHaveBeenCalledWith('bob');
      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ clientId: 'earlier-id' });
      expect(identifyEntries()[0].clientId).toBe('earlier-id');
    });

    it('should let the settings beat a disagreeing cache, and refresh it', async () => {
      set(mockClientId, 'settings-id');
      mockReadCachedClientId.mockReturnValue('stale-id');
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(identifyEntries()[0].clientId).toBe('settings-id');
      expect(mockCacheClientId).toHaveBeenCalledWith('bob', 'settings-id');
      expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
    });

    it('should cache under the account that resolved it', async () => {
      set(mockUsername, 'alice');
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(mockCacheClientId).toHaveBeenCalledWith('alice', 'minted-id');
    });

    it('should not cache a value the write failed to persist', async () => {
      mockUpdateFrontendSetting.mockResolvedValue({ success: false, message: 'nope' });
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(mockCacheClientId).not.toHaveBeenCalled();
    });

    it('should not identify with a value the write failed to persist', async () => {
      mockUpdateFrontendSetting.mockResolvedValue({ success: false, message: 'nope' });
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(identifyEntries()).toHaveLength(0);
    });

    it('should not resolve one while the gate is closed', async () => {
      set(mockClientId, 'existing-id');
      set(mockLogged, true);
      set(mockSubmitUsageAnalytics, false);

      scope.run(() => useSigil());
      await flushPromises();

      expect(identifyEntries()).toHaveLength(0);
      expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
    });
  });

  describe('identify entry', () => {
    it('should carry the instance value as session data', async () => {
      set(mockClientId, 'existing-id');
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(identifyEntries()[0].data).toEqual({ instance_id: 'instance-1' });
    });

    /** Upstream classifies by name, so a named identify would be recorded as a custom event. */
    it('should not be named', async () => {
      set(mockClientId, 'existing-id');
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(identifyEntries()[0].name).toBeUndefined();
    });

    it('should set the value events are stamped with', async () => {
      set(mockClientId, 'existing-id');
      activateSigil();

      scope.run(() => useSigil());
      await flushPromises();

      expect(mockSetCurrentClientId).toHaveBeenCalledWith('existing-id');
    });

    it('should drop that value on deactivate, before the queue drains', async () => {
      set(mockClientId, 'existing-id');
      activateSigil();
      scope.run(() => useSigil());
      await flushPromises();

      set(mockLogged, false);
      await nextTick();

      expect(mockClearCurrentClientId).toHaveBeenCalled();
      expect(mockClearCurrentClientId.mock.invocationCallOrder[0])
        .toBeLessThan(mockStopQueue.mock.invocationCallOrder[0]);
    });

    it('should be queued before the events of that session', async () => {
      set(mockClientId, 'existing-id');
      activateSigil();
      scope.run(() => useSigil());
      await flushPromises();

      sigilBus.emit('session:ready');
      await flushPromises();

      const kinds = mockEnqueue.mock.calls.map(call => call[0].kind ?? 'event');
      expect(kinds[0]).toBe('identify');
      expect(kinds).toContain('event');
    });
  });

  describe('chronicle one-shot', () => {
    it('should emit session_config and exchanges_summary on session:ready', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      sigilBus.emit('session:ready');
      await flushPromises();

      const eventNames = mockEnqueue.mock.calls.map(
        call => call[0].name,
      );
      expect(eventNames).toContain('session_config');
      expect(eventNames).toContain('exchanges_summary');
    });

    it('should emit balances_summary on balances:loaded', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      sigilBus.emit('balances:loaded');
      await nextTick();

      const eventNames = mockEnqueue.mock.calls.map(
        call => call[0].name,
      );
      expect(eventNames).toContain('balances_summary');
    });

    it('should emit history_sync on history:ready', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      sigilBus.emit('history:ready');
      // Allow the async promise chain in onHistoryReady to resolve
      await flushPromises();

      const eventNames = mockEnqueue.mock.calls.map(
        call => call[0].name,
      );
      expect(eventNames).toContain('history_sync');
    });

    it('should deduplicate repeated bus emissions', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      sigilBus.emit('session:ready');
      sigilBus.emit('session:ready');
      sigilBus.emit('session:ready');
      await flushPromises();

      const sessionCalls = mockEnqueue.mock.calls.filter(
        call => call[0].name === 'session_config',
      );
      expect(sessionCalls).toHaveLength(1);
    });

    it('should reset deduplication after deactivate/reactivate cycle', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      sigilBus.emit('session:ready');
      await flushPromises();

      // Deactivate
      set(mockLogged, false);
      await nextTick();

      // Reactivate
      mockEnqueue.mockClear();
      set(mockLogged, true);
      await nextTick();

      sigilBus.emit('session:ready');
      await flushPromises();

      const sessionCalls = mockEnqueue.mock.calls.filter(
        call => call[0].name === 'session_config',
      );
      expect(sessionCalls).toHaveLength(1);
    });
  });

  describe('page tracking', () => {
    it('should register router afterEach on activate', async () => {
      const { router } = await import('@/router');
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      // eslint-disable-next-line @typescript-eslint/unbound-method
      expect(router.afterEach).toHaveBeenCalled();
      expect(afterEachCallback).toBeDefined();
    });

    it('should enqueue page views via router hook', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      mockEnqueue.mockClear();
      afterEachCallback?.({
        name: 'balances',
        params: { location: 'eth2' },
        matched: [{ path: '/staking/:location' }],
      });
      await nextTick();

      expect(mockEnqueue).toHaveBeenCalledWith(
        expect.objectContaining({
          url: '/staking/eth2',
        }),
      );
    });

    it('should redact unsafe route params', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      mockEnqueue.mockClear();
      afterEachCallback?.({
        name: 'account-detail',
        params: { address: '0xSensitive123' },
        matched: [{ path: '/accounts/:address' }],
      });
      await nextTick();

      const call = mockEnqueue.mock.calls[0];
      expect(call[0].url).toBe('/accounts/:address');
    });

    it('should resolve safe params like location and exchange', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      mockEnqueue.mockClear();
      afterEachCallback?.({
        name: 'exchange-balances',
        params: { exchange: 'binance', tab: 'deposits' },
        matched: [{ path: '/balances/:exchange/:tab' }],
      });
      await nextTick();

      const call = mockEnqueue.mock.calls[0];
      expect(call[0].url).toBe('/balances/binance/deposits');
    });
  });

  describe('chronicle payload', () => {
    it('should include event name and data in enqueued entry', async () => {
      activateSigil();
      scope.run(() => useSigil());
      await nextTick();

      sigilBus.emit('session:ready');
      await flushPromises();

      const sessionCall = mockEnqueue.mock.calls.find(
        call => call[0].name === 'session_config',
      );
      expect(sessionCall).toBeDefined();

      const entry = sessionCall![0];
      expect(entry.name).toBe('session_config');
      expect(entry.data).toMatchObject({ premium: false, appVersion: '1.0' });
      expect(entry.url).toBe('/dashboard');
      expect(entry.timestamp).toBeTypeOf('number');
    });
  });
});
