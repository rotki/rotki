import type { BankConnection } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankBalancesPage } from '@/pages/balances/banks/use-bank-balances-page';

const { fetchBankBalances, refreshBankConnections } = vi.hoisted(() => ({
  fetchBankBalances: vi.fn<(ignoreCache?: boolean, connection?: { identifier: string }) => Promise<void>>(),
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
    bankCode: null,
    displayName: 'FinTS/HBCI',
    identifier: `id-${name}`,
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
      connection('ING', { authChallenge: { challenge: null, challengeData: null, challengeHtml: null, challengeMimeType: null, identifier: 'id-ING', primitive: 'otp input', prompt: 'TAN' } }),
      connection('Comdirect'),
    ]);
    useBalancesStore().bankBalances = [
      { accounts: [], balances: eur(100), connector: 'fints', identifier: 'id-DKB', name: 'DKB' },
      { accounts: [], balances: eur(2), connector: 'fints', identifier: 'id-ING', name: 'ING' },
    ];
  });

  it('should list every bank together without a selection', () => {
    const { balances, selectedBank } = useBankBalancesPage(() => undefined);

    expect(get(selectedBank)).toBeUndefined();
    expect(get(balances).map(row => [row.asset, row.amount.toFixed()])).toEqual([['EUR', '102']]);
  });

  it('should list only the selected bank', () => {
    const { balances, selectedBank } = useBankBalancesPage(() => 'id-ING');

    expect(get(selectedBank)?.name).toBe('ING');
    expect(get(balances).map(row => [row.asset, row.amount.toFixed()])).toEqual([['EUR', '2']]);
  });

  it('should keep the selected bank and its balances after its name changes', () => {
    const store = useBankConnectionsStore();
    const { balances, selectedBank } = useBankBalancesPage(() => 'id-ING');

    store.setConnections([
      { ...connection('Renamed'), identifier: 'id-ING' },
      { ...connection('ING'), identifier: 'another-connection' },
    ]);

    expect(get(selectedBank)?.name).toBe('Renamed');
    expect(get(selectedBank)?.identifier).toBe('id-ING');
    expect(get(balances).map(row => row.amount.toFixed())).toEqual(['2']);
  });

  it('should fall back to every bank when the selected one is gone', () => {
    const { balances, selectedBank } = useBankBalancesPage(() => 'Removed');

    expect(get(selectedBank)).toBeUndefined();
    expect(get(balances)).toHaveLength(1);
  });

  it('should list the connections in view that need the user, a pending TAN first', () => {
    expect(get(useBankBalancesPage(() => undefined).issues).map(({ name }) => name)).toEqual(['ING', 'DKB']);
    expect(get(useBankBalancesPage(() => 'id-DKB').issues).map(({ name }) => name)).toEqual(['DKB']);
    expect(get(useBankBalancesPage(() => 'id-Comdirect').issues)).toEqual([]);
  });

  it('should refresh only the bank in view, bypassing the cache', async () => {
    await useBankBalancesPage(() => 'id-ING').refreshInView();

    expect(fetchBankBalances).toHaveBeenCalledExactlyOnceWith(true, { identifier: 'id-ING' });
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

    const refreshing = refreshBank({ identifier: 'id-DKB' });
    expect(isBankLoading('id-DKB')).toBe(true);
    expect(isBankLoading('id-ING')).toBe(false);

    finish();
    await refreshing;
    expect(isBankLoading('id-DKB')).toBe(false);
  });
});
