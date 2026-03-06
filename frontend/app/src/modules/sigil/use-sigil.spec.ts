import type { SigilEventMap } from '@/modules/sigil/types';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { sigilBus } from '@/modules/sigil/event-bus';

const mockEnqueue = vi.fn().mockResolvedValue(undefined);
const mockStartQueue = vi.fn();
const mockStopQueue = vi.fn();

vi.mock('@/modules/sigil/use-sigil-queue', () => ({
  WEBSITE_ID: 'test-website-id',
  enqueue: (...args: unknown[]): unknown => mockEnqueue(...args),
  startQueue: (): void => mockStartQueue(),
  stopQueue: (): void => mockStopQueue(),
}));

const mockSessionConfig: SigilEventMap['session_config'] = {
  premium: false,
  appVersion: '1.0',
  mainCurrency: 'USD',
  language: 'en',
  theme: 'auto',
  appMode: 'web',
  priceOracles: '',
};

const mockExchangesSummary: SigilEventMap['exchanges_summary'] = { exchangeCount: 0 };
const mockBalancesSummary: SigilEventMap['balances_summary'] = { hasManualBalances: false, distinctAssetCount: 0, totalAccounts: 0, totalChains: 0 };
const mockHistorySync: SigilEventMap['history_sync'] = { totalEvents: 10, spamEvents: 2, totalGroups: 5 };

vi.mock('@/modules/sigil/handlers/session-config', () => ({
  useSessionConfigHandler: vi.fn(() => (): SigilEventMap['session_config'] => ({ ...mockSessionConfig })),
}));

vi.mock('@/modules/sigil/handlers/exchanges-summary', () => ({
  useExchangesSummaryHandler: vi.fn(() => (): SigilEventMap['exchanges_summary'] => ({ ...mockExchangesSummary })),
}));

vi.mock('@/modules/sigil/handlers/balances-summary', () => ({
  useBalancesSummaryHandler: vi.fn(() => (): SigilEventMap['balances_summary'] => ({ ...mockBalancesSummary })),
}));

vi.mock('@/modules/sigil/handlers/history-sync', () => ({
  useHistorySyncHandler: vi.fn(() => async (): Promise<SigilEventMap['history_sync']> => Promise.resolve({ ...mockHistorySync })),
}));

const mockLogged = ref<boolean>(false);
const mockSubmitUsageAnalytics = ref<boolean>(false);
const mockIsDevelop = ref<boolean>(false);

vi.mock('@/store/session/auth', () => ({
  useSessionAuthStore: vi.fn(() => ({
    $id: 'session/auth',
    logged: mockLogged,
  })),
}));

vi.mock('@/store/settings/general', () => ({
  useGeneralSettingsStore: vi.fn(() => ({
    $id: 'settings/general',
    submitUsageAnalytics: mockSubmitUsageAnalytics,
  })),
}));

vi.mock('@/store/main', () => ({
  useMainStore: vi.fn(() => ({
    $id: 'main',
    isDevelop: mockIsDevelop,
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

const { useSigil } = await import('@/modules/sigil/use-sigil');

function activateSigil(): void {
  set(mockLogged, true);
  set(mockSubmitUsageAnalytics, true);
  set(mockIsDevelop, false);
}

describe('useSigil', () => {
  beforeEach(() => {
    mockEnqueue.mockClear();
    mockStartQueue.mockClear();
    mockStopQueue.mockClear();
    mockRemoveHook.mockClear();
    set(mockLogged, false);
    set(mockSubmitUsageAnalytics, false);
    set(mockIsDevelop, false);
    afterEachCallback = undefined;
    sigilBus.all.clear();
  });

  describe('activation gate', () => {
    it('should not activate when not logged in', async () => {
      useSigil();
      await nextTick();
      expect(mockStartQueue).not.toHaveBeenCalled();
    });

    it('should not activate when analytics disabled', async () => {
      set(mockLogged, true);
      set(mockSubmitUsageAnalytics, false);

      useSigil();
      await nextTick();
      expect(mockStartQueue).not.toHaveBeenCalled();
    });

    it('should not activate in dev mode without debug flag', async () => {
      set(mockLogged, true);
      set(mockSubmitUsageAnalytics, true);
      set(mockIsDevelop, true);

      useSigil();
      await nextTick();
      expect(mockStartQueue).not.toHaveBeenCalled();
    });

    it('should activate when all conditions met', async () => {
      activateSigil();

      useSigil();
      await nextTick();
      expect(mockStartQueue).toHaveBeenCalledOnce();
    });
  });

  describe('deactivation', () => {
    it('should deactivate when user logs out', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      set(mockLogged, false);
      await nextTick();

      expect(mockStopQueue).toHaveBeenCalled();
    });

    it('should deactivate when analytics toggled off', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      set(mockSubmitUsageAnalytics, false);
      await nextTick();

      expect(mockStopQueue).toHaveBeenCalled();
    });

    it('should unregister router hook on deactivate', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      set(mockLogged, false);
      await nextTick();

      expect(mockRemoveHook).toHaveBeenCalled();
    });
  });

  describe('chronicle one-shot', () => {
    it('should emit session_config and exchanges_summary on session:ready', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      sigilBus.emit('session:ready');
      await nextTick();

      const eventNames = mockEnqueue.mock.calls.map(
        (call: unknown[]) => (call[0] as Record<string, unknown>).name,
      );
      expect(eventNames).toContain('session_config');
      expect(eventNames).toContain('exchanges_summary');
    });

    it('should emit balances_summary on balances:loaded', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      sigilBus.emit('balances:loaded');
      await nextTick();

      const eventNames = mockEnqueue.mock.calls.map(
        (call: unknown[]) => (call[0] as Record<string, unknown>).name,
      );
      expect(eventNames).toContain('balances_summary');
    });

    it('should emit history_sync on history:ready', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      sigilBus.emit('history:ready');
      // Allow the async promise chain in onHistoryReady to resolve
      await flushPromises();

      const eventNames = mockEnqueue.mock.calls.map(
        (call: unknown[]) => (call[0] as Record<string, unknown>).name,
      );
      expect(eventNames).toContain('history_sync');
    });

    it('should deduplicate repeated bus emissions', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      sigilBus.emit('session:ready');
      sigilBus.emit('session:ready');
      sigilBus.emit('session:ready');
      await nextTick();

      const sessionCalls = mockEnqueue.mock.calls.filter(
        (call: unknown[]) => (call[0] as Record<string, unknown>).name === 'session_config',
      );
      expect(sessionCalls).toHaveLength(1);
    });

    it('should reset deduplication after deactivate/reactivate cycle', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      sigilBus.emit('session:ready');
      await nextTick();

      // Deactivate
      set(mockLogged, false);
      await nextTick();

      // Reactivate
      mockEnqueue.mockClear();
      set(mockLogged, true);
      await nextTick();

      sigilBus.emit('session:ready');
      await nextTick();

      const sessionCalls = mockEnqueue.mock.calls.filter(
        (call: unknown[]) => (call[0] as Record<string, unknown>).name === 'session_config',
      );
      expect(sessionCalls).toHaveLength(1);
    });
  });

  describe('page tracking', () => {
    it('should register router afterEach on activate', async () => {
      const { router } = await import('@/router');
      activateSigil();
      useSigil();
      await nextTick();

      // eslint-disable-next-line @typescript-eslint/unbound-method
      expect(router.afterEach).toHaveBeenCalled();
      expect(afterEachCallback).toBeDefined();
    });

    it('should enqueue page views via router hook', async () => {
      activateSigil();
      useSigil();
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
      useSigil();
      await nextTick();

      mockEnqueue.mockClear();
      afterEachCallback?.({
        name: 'account-detail',
        params: { address: '0xSensitive123' },
        matched: [{ path: '/accounts/:address' }],
      });
      await nextTick();

      const call = mockEnqueue.mock.calls[0] as [Record<string, unknown>];
      expect(call[0].url).toBe('/accounts/:address');
    });

    it('should resolve safe params like location and exchange', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      mockEnqueue.mockClear();
      afterEachCallback?.({
        name: 'exchange-balances',
        params: { exchange: 'binance', tab: 'deposits' },
        matched: [{ path: '/balances/:exchange/:tab' }],
      });
      await nextTick();

      const call = mockEnqueue.mock.calls[0] as [Record<string, unknown>];
      expect(call[0].url).toBe('/balances/binance/deposits');
    });
  });

  describe('chronicle payload', () => {
    it('should include event name and data in enqueued entry', async () => {
      activateSigil();
      useSigil();
      await nextTick();

      sigilBus.emit('session:ready');
      await nextTick();

      const sessionCall = mockEnqueue.mock.calls.find(
        (call: unknown[]) => (call[0] as Record<string, unknown>).name === 'session_config',
      );
      expect(sessionCall).toBeDefined();

      const entry = sessionCall![0] as Record<string, unknown>;
      expect(entry.name).toBe('session_config');
      expect(entry.data).toMatchObject({ premium: false, appVersion: '1.0' });
      expect(entry.url).toBe('/dashboard');
      expect(entry.timestamp).toBeTypeOf('number');
    });
  });
});
