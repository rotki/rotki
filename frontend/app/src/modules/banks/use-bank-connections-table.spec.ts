import type { BankConnection } from '@/modules/banks/types';
import { createTestBankConnection as connection, createTestBalance } from '@test/utils/create-data';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankConnectionsTable } from '@/modules/banks/use-bank-connections-table';

describe('useBankConnectionsTable', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useBankConnectionsStore().setConnections([connection('qonto', 'Business'), connection('fints', 'Checking')]);
    useBalancesStore().bankBalances = [
      { accounts: [], balances: { EUR: createTestBalance(200, 200), SPAM: createTestBalance(5000, 5000) }, connector: 'qonto', identifier: 'qonto-Business', name: 'Business' },
      { accounts: [], balances: { EUR: createTestBalance(300, 300) }, connector: 'fints', identifier: 'fints-Checking', name: 'Checking' },
    ];
  });

  it('should give each connection its own balance', () => {
    useAssetsStore().ignoredAssets = ['SPAM'];
    const { balanceOf } = useBankConnectionsTable(vi.fn<(row: BankConnection) => Promise<boolean>>());

    expect(balanceOf(connection('qonto', 'Business')).toFixed()).toBe('200');
    expect(balanceOf(connection('fints', 'Checking')).toFixed()).toBe('300');
  });

  it('should match a connection by its identifier, not by a name another bank shares', () => {
    const { balanceOf } = useBankConnectionsTable(vi.fn<(row: BankConnection) => Promise<boolean>>());

    expect(balanceOf(connection('fints', 'Business')).toFixed()).toBe('0');
  });

  it('should give zero to a connection that has not reported a balance yet', () => {
    useBankConnectionsStore().setConnections([connection('qonto', 'Business'), connection('fints', 'Savings')]);
    const { balanceOf } = useBankConnectionsTable(vi.fn<(row: BankConnection) => Promise<boolean>>());

    expect(balanceOf(connection('fints', 'Savings')).toFixed()).toBe('0');
  });

  it('should mark a connection as syncing until its sync settles, failed or not, and follow the backend otherwise', async () => {
    const { isSyncing, whileSyncing } = useBankConnectionsTable(vi.fn<(row: BankConnection) => Promise<boolean>>());
    const business = connection('qonto', 'Business');
    let finish: () => void = () => {};
    const sync = vi.fn<() => Promise<void>>(async () => new Promise<void>((_resolve, reject) => {
      finish = (): void => reject(new Error('bank down'));
    }));

    const running = whileSyncing(business, sync);
    expect(isSyncing(business)).toBe(true);
    expect(isSyncing(connection('fints', 'Business'))).toBe(false);
    finish();
    await expect(running).rejects.toThrow('bank down');

    expect(isSyncing(business)).toBe(false);
    expect(isSyncing(connection('qonto', 'Business', { running: true }))).toBe(true);
  });

  it('should show a value column between the last sync and the actions', () => {
    const { cols } = useBankConnectionsTable(vi.fn<(row: BankConnection) => Promise<boolean>>());

    expect(get(cols).map(col => col.key)).toStrictEqual(['connector', 'name', 'syncStatus', 'balance', 'actions']);
  });

  it('should name a refused removal above the table and keep the row', async () => {
    const removeBank = vi.fn<(row: BankConnection) => Promise<boolean>>().mockRejectedValue(new Error('gone'));
    const { removeFailure, removeRow } = useBankConnectionsTable(removeBank);

    await removeRow(connection('qonto', 'Business'));

    expect(removeBank).toHaveBeenCalledOnce();
    expect(get(removeFailure)?.title).toBe('bank_settings.errors.remove_title');
  });
});
