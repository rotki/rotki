import type { BankConnection, BankManifest } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanks } from '@/modules/banks/use-banks';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const {
  addBank,
  editBank,
  getBanks,
  getSupportedBanks,
  notifyError,
  queryAllBankEvents,
  queryBankBalances,
  removeBank,
  submitTask,
} = vi.hoisted(() => ({
  addBank: vi.fn(),
  editBank: vi.fn(),
  getBanks: vi.fn(),
  getSupportedBanks: vi.fn(),
  notifyError: vi.fn(),
  queryAllBankEvents: vi.fn(),
  queryBankBalances: vi.fn(),
  removeBank: vi.fn(),
  submitTask: vi.fn(),
}));

vi.mock('@/modules/banks/use-banks-api', () => ({
  useBanksApi: (): Record<string, unknown> => ({
    addBank,
    editBank,
    getBanks,
    getSupportedBanks,
    queryBankBalances,
    removeBank,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): Record<string, unknown> => ({ notifyError }),
}));

vi.mock('@/modules/history/events/tx/use-bank-events-refresh', () => ({
  useBankEventsRefresh: (): Record<string, unknown> => ({ queryAllBankEvents }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): Record<string, unknown> => ({ submitTask }),
}));

const manifest: BankManifest = {
  accessTier: 'official api',
  authFlow: [{ primitive: 'static secret' }],
  capabilities: ['balances'],
  displayName: 'Qonto',
  docsUrl: 'https://docs.qonto.com',
  location: 'qonto',
  maintainer: 'rotki',
  secrets: [{ description: '', label: 'Login', slot: 'api_key' }],
  setupNotes: [],
  version: '1.0.0',
};

const connection: BankConnection = {
  displayName: 'Qonto',
  location: 'qonto',
  name: 'Qonto main',
  syncStatus: { lastError: null, lastSyncTs: null, running: false },
};

const eur = { EUR: { amount: bigNumberify(10), value: bigNumberify(11) } };
const eurOnTheWire = { EUR: { amount: '10', value: '11' } };

describe('useBanks', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    getBanks.mockResolvedValue([connection]);
    getSupportedBanks.mockResolvedValue([manifest]);
    queryAllBankEvents.mockResolvedValue([ok(undefined)]);
    // the task runner hands the api result straight to the `run` callback
    submitTask.mockImplementation(async spec => spec.run({ runTask: async (fn: () => Promise<unknown>) => ok(await fn()) }));
    queryBankBalances.mockResolvedValue({ qonto: eurOnTheWire });
    useLocationStore().$patch({ allLocations: { kraken: { image: 'kraken.svg' }, qonto: { image: 'qonto.svg', isBank: true } } });
  });

  it('should store the supported banks and connections it fetches', async () => {
    const banks = useBanks();
    const store = useBankConnectionsStore();
    await banks.refreshSupportedBanks();
    await banks.refreshBankConnections();
    expect(store.manifests).toEqual([manifest]);
    expect(store.connections).toEqual([connection]);
    expect(store.manifestFor('qonto')).toEqual(manifest);
  });

  it('should add through PUT and edit through PATCH, dropping an unchanged new name', async () => {
    addBank.mockResolvedValue(true);
    editBank.mockResolvedValue(true);
    const banks = useBanks();
    const credentials = { api_key: 'login' };

    await banks.setupBank({ credentials, location: 'qonto', mode: 'add', name: 'Qonto main', newName: '' });
    expect(addBank).toHaveBeenCalledWith({ credentials, location: 'qonto', name: 'Qonto main' });

    await banks.setupBank({ credentials, location: 'qonto', mode: 'edit', name: 'Qonto main', newName: 'Qonto main' });
    expect(editBank).toHaveBeenCalledWith({ credentials, location: 'qonto', name: 'Qonto main', newName: undefined });

    await banks.setupBank({ credentials, location: 'qonto', mode: 'edit', name: 'Qonto main', newName: 'Renamed' });
    expect(editBank).toHaveBeenLastCalledWith({ credentials, location: 'qonto', name: 'Qonto main', newName: 'Renamed' });
    expect(getBanks).toHaveBeenCalledTimes(3);
  });

  it('should let a setup error propagate so the dialog can map it onto fields', async () => {
    addBank.mockRejectedValue(new Error('bank said no'));
    const banks = useBanks();
    await expect(banks.setupBank({ credentials: {}, location: 'qonto', mode: 'add', name: 'x', newName: '' }))
      .rejects
      .toThrow('bank said no');
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should notify instead of throwing when removal fails', async () => {
    removeBank.mockRejectedValue(new Error('gone'));
    const banks = useBanks();
    expect(await banks.removeBank(connection)).toBe(false);
    expect(notifyError).toHaveBeenCalledOnce();
  });

  it('should sync the picked connection through the bank events activity and refresh the status', async () => {
    const both = [connection, { ...connection, name: 'Qonto side' }];
    getBanks.mockResolvedValue(both);
    useBankConnectionsStore().setConnections(both);
    const banks = useBanks();
    expect(await banks.syncBanks({ location: 'qonto', name: 'Qonto main' })).toBe(true);
    expect(queryAllBankEvents).toHaveBeenCalledWith([{ location: 'qonto', name: 'Qonto main' }]);
    expect(getBanks).toHaveBeenCalledOnce();

    await banks.syncBanks();
    expect(queryAllBankEvents).toHaveBeenLastCalledWith([
      { location: 'qonto', name: 'Qonto main' },
      { location: 'qonto', name: 'Qonto side' },
    ]);
  });

  it('should report a failed sync as false', async () => {
    useBankConnectionsStore().setConnections([connection]);
    queryAllBankEvents.mockResolvedValue([err(TaskFailed({ message: 'boom' }))]);
    expect(await useBanks().syncBanks()).toBe(false);
  });

  it('should write bank balances next to exchange balances and drop them when no connection is left', async () => {
    const balances = useBalancesStore();
    balances.exchangeBalances = { kraken: eur };
    const store = useBankConnectionsStore();
    store.setConnections([connection]);
    const banks = useBanks();

    await banks.fetchBankBalances(true);
    expect(queryBankBalances).toHaveBeenCalledWith(true);
    expect(Object.keys(balances.exchangeBalances).sort()).toEqual(['kraken', 'qonto']);

    store.setConnections([]);
    await banks.fetchBankBalances();
    expect(queryBankBalances).toHaveBeenCalledOnce();
    expect(Object.keys(balances.exchangeBalances)).toEqual(['kraken']);
  });
});
