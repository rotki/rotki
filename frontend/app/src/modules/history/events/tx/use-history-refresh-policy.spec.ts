import type { Exchange } from '@/modules/balances/types/exchanges';
import type { BankConnection, BankConnectionIdentity } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useHistoryRefreshPolicy } from '@/modules/history/events/tx/use-history-refresh-policy';

const mocks = vi.hoisted(() => {
  const attempted = new Set<string>();
  return {
    attempted,
    statusOf: vi.fn((kind: string, ...parts: (string | number)[]) => ({
      lastOutcome: attempted.has([kind, ...parts].join(':')) ? 'success' : undefined,
    })),
  };
});

vi.mock('@/modules/balances/exchanges/use-exchange-data', () => ({
  useExchangeData: (): Record<string, unknown> => ({
    isSameExchange: (a: Exchange, b: Exchange): boolean => a.location === b.location && a.name === b.name,
    syncingExchanges: ref<Exchange[]>([]),
  }),
}));

vi.mock('@/modules/history/events/tx/use-history-transaction-accounts', () => ({
  useHistoryTransactionAccounts: (): Record<string, unknown> => ({ getAllAccounts: vi.fn(() => []) }),
}));

vi.mock('@/modules/settings/general/disabled-chain-queries/use-disabled-chains', () => ({
  useDisabledChains: (): Record<string, unknown> => ({ filterAccounts: vi.fn((accounts: unknown[]) => accounts) }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({ isDecodableChains: vi.fn(() => true) }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): Record<string, unknown> => ({ statusOf: mocks.statusOf }),
}));

const main: BankConnectionIdentity = { location: 'qonto', name: 'rotki Solutions GmbH' };
const side: BankConnectionIdentity = { location: 'qonto', name: 'Side organization' };

function connection(identity: BankConnectionIdentity): BankConnection {
  return { ...identity, displayName: 'Qonto', syncStatus: { lastError: null, lastSyncTs: null, running: false } };
}

const noNovelty = { newAccounts: [], newBanks: [], newExchanges: [] };

const baseOptions = {
  chains: [],
  everRefreshed: true,
  fullRefresh: false,
  inputAccounts: [],
  usedBanks: [],
  usedExchanges: [],
  userInitiated: false,
};

describe('useHistoryRefreshPolicy', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    mocks.attempted.clear();
    useBankConnectionsStore().setConnections([connection(main), connection(side)]);
  });

  describe('filterSyncingBanks', () => {
    it('should sync every connection when no banks are picked', () => {
      expect(useHistoryRefreshPolicy().filterSyncingBanks(undefined)).toEqual([main, side]);
    });

    it('should drop picked banks that are not connected', () => {
      const unknown = { location: 'qonto', name: 'Removed organization' };
      expect(useHistoryRefreshPolicy().filterSyncingBanks([side, unknown])).toEqual([side]);
    });
  });

  describe('detectNovelty', () => {
    it('should report only the bank connections that never finished a sync attempt', () => {
      mocks.attempted.add(`bank-events:${main.location}:${main.name}`);
      const { newBanks } = useHistoryRefreshPolicy().detectNovelty([], [], [main, side]);
      expect(newBanks).toEqual([side]);
    });
  });

  describe('shouldNotRefresh', () => {
    it('should refresh a loaded history when a bank connection is new', () => {
      const { shouldNotRefresh } = useHistoryRefreshPolicy();
      expect(shouldNotRefresh({ alreadyLoaded: true, novelty: { ...noNovelty, newBanks: [side] } })).toBe(false);
      expect(shouldNotRefresh({ alreadyLoaded: true, novelty: noNovelty })).toBe(true);
    });
  });

  describe('resolveRefreshTargets', () => {
    it('should cover every connected bank on a full refresh', () => {
      const targets = useHistoryRefreshPolicy().resolveRefreshTargets({}, noNovelty, { ...baseOptions, fullRefresh: true });
      expect(targets).toMatchObject({ banks: [main, side], queryBanks: true });
    });

    it('should query the picked banks when the caller names them', () => {
      const targets = useHistoryRefreshPolicy().resolveRefreshTargets({ banks: [side] }, noNovelty, { ...baseOptions, usedBanks: [side] });
      expect(targets).toMatchObject({ banks: [side], queryBanks: true, usedBanks: [side] });
    });

    it('should narrow to the new bank connections when a background refresh finds some', () => {
      const targets = useHistoryRefreshPolicy().resolveRefreshTargets({}, { ...noNovelty, newBanks: [side] }, baseOptions);
      expect(targets).toMatchObject({ banks: [side], shouldShowSyncProgress: true });
    });

    it('should not query banks when neither a full refresh nor a bank payload asks for them', () => {
      const targets = useHistoryRefreshPolicy().resolveRefreshTargets({}, noNovelty, baseOptions);
      expect(targets).toMatchObject({ banks: [], queryBanks: false });
    });
  });
});
