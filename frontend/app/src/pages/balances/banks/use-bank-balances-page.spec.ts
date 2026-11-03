import type { BankConnection } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankBalancesPage } from '@/pages/balances/banks/use-bank-balances-page';

const { fetchBankBalances, refreshBankConnections } = vi.hoisted(() => ({
  fetchBankBalances: vi.fn<(ignoreCache?: boolean, connection?: { connector: string; name: string }) => Promise<void>>(),
  refreshBankConnections: vi.fn<() => Promise<void>>(),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({ fetchBankBalances, refreshBankConnections }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({
    useIsActive: (): unknown => ref<boolean>(false),
    useIsActivePrefix: (): unknown => ref<boolean>(false),
  }),
}));

function connection(name: string, syncStatus: Partial<BankConnection['syncStatus']> = {}): BankConnection {
  return {
    connector: 'fints',
    displayName: 'FinTS/HBCI',
    name,
    syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false, ...syncStatus },
  };
}

function eur(amount: number): { EUR: { amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> } } {
  return { EUR: { amount: bigNumberify(amount), value: bigNumberify(amount) } };
}

describe('useBankBalancesPage', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    fetchBankBalances.mockResolvedValue(undefined);
    refreshBankConnections.mockResolvedValue(undefined);
    const store = useBankConnectionsStore();
    store.setConnections([
      connection('DKB', { lastError: 'boom' }),
      connection('ING', { authChallenge: { challenge: null, challengeData: null, challengeHtml: null, challengeMimeType: null, primitive: 'otp input', prompt: 'TAN' } }),
      connection('Comdirect'),
    ]);
    store.setConnectionBalances([
      { accounts: [], balances: eur(100), connector: 'fints', name: 'DKB' },
      { accounts: [], balances: eur(2), connector: 'fints', name: 'ING' },
    ]);
  });

  it('should list every bank together without a selection', () => {
    const { balances, selectedBank } = useBankBalancesPage(() => undefined);

    expect(get(selectedBank)).toBeUndefined();
    expect(get(balances).map(row => [row.asset, row.amount.toFixed()])).toEqual([['EUR', '102']]);
  });

  it('should list only the selected bank', () => {
    const { balances, selectedBank } = useBankBalancesPage(() => 'ING');

    expect(get(selectedBank)?.name).toBe('ING');
    expect(get(balances).map(row => [row.asset, row.amount.toFixed()])).toEqual([['EUR', '2']]);
  });

  it('should fall back to every bank when the selected one is gone', () => {
    const { balances, selectedBank } = useBankBalancesPage(() => 'Removed');

    expect(get(selectedBank)).toBeUndefined();
    expect(get(balances)).toHaveLength(1);
  });

  it('should list the connections in view that need the user, a pending TAN first', () => {
    expect(get(useBankBalancesPage(() => undefined).issues).map(({ name }) => name)).toEqual(['ING', 'DKB']);
    expect(get(useBankBalancesPage(() => 'DKB').issues).map(({ name }) => name)).toEqual(['DKB']);
    expect(get(useBankBalancesPage(() => 'Comdirect').issues)).toEqual([]);
  });

  it('should refresh only the bank in view, bypassing the cache', async () => {
    await useBankBalancesPage(() => 'ING').refreshInView();

    expect(fetchBankBalances).toHaveBeenCalledExactlyOnceWith(true, { connector: 'fints', name: 'ING' });
    expect(refreshBankConnections).not.toHaveBeenCalled();
  });

  it('should refresh every bank and its connection status when all are in view', async () => {
    await useBankBalancesPage(() => undefined).refreshInView();

    expect(refreshBankConnections).toHaveBeenCalledOnce();
    expect(fetchBankBalances).toHaveBeenCalledExactlyOnceWith(true);
  });

  it('should mark a bank as loading only while it is refreshed on its own', async () => {
    let finish: () => void = () => {};
    fetchBankBalances.mockReturnValue(new Promise<void>((resolve) => {
      finish = resolve;
    }));
    const { isBankLoading, refreshBank } = useBankBalancesPage(() => undefined);

    const refreshing = refreshBank({ connector: 'fints', name: 'DKB' });
    expect(isBankLoading('DKB')).toBe(true);
    expect(isBankLoading('ING')).toBe(false);

    finish();
    await refreshing;
    expect(isBankLoading('DKB')).toBe(false);
  });
});
