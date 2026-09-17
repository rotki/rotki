import type { BankAuthenticationRequest, BankConnection, BankManifest, BankSetupError } from '@/modules/banks/types';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
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
  answerAuthentication,
  editBank,
  getBanks,
  getSupportedBanks,
  notifyError,
  notifyInfo,
  queryAllBankEvents,
  queryBankBalances,
  removeBank,
  submitTask,
} = vi.hoisted(() => ({
  addBank: vi.fn(),
  answerAuthentication: vi.fn(),
  editBank: vi.fn(),
  getBanks: vi.fn(),
  getSupportedBanks: vi.fn(),
  notifyError: vi.fn(),
  notifyInfo: vi.fn(),
  queryAllBankEvents: vi.fn(),
  queryBankBalances: vi.fn(),
  removeBank: vi.fn(),
  submitTask: vi.fn(),
}));

vi.mock('@/modules/banks/use-banks-api', () => ({
  useBanksApi: (): Record<string, unknown> => ({
    addBank,
    answerAuthentication,
    editBank,
    getBanks,
    getSupportedBanks,
    queryBankBalances,
    removeBank,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): Record<string, unknown> => ({ notifyError, notifyInfo }),
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
  secrets: [{ description: '', label: 'Login', secret: true, slot: 'api_key' }],
  setupNotes: [],
  version: '1.0.0',
};

const connection: BankConnection = {
  displayName: 'Qonto',
  location: 'qonto',
  name: 'Qonto main',
  syncStatus: { authChallenge: null, lastError: null, lastSyncTs: null, running: false },
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

  it('should add through PUT and edit through PATCH, dropping an unchanged new name and refreshing after each setup, balance query and sync', async () => {
    addBank.mockResolvedValue(ok({ historyStartTs: null, success: true }));
    editBank.mockResolvedValue(ok(true));
    const banks = useBanks();
    const credentials = { api_key: 'login' };

    await banks.setupBank({ credentials, location: 'qonto', mode: 'add', name: 'Qonto main', newName: '' });
    await flushPromises();
    expect(addBank).toHaveBeenCalledWith({ credentials, location: 'qonto', name: 'Qonto main' });

    await banks.setupBank({ credentials, location: 'qonto', mode: 'edit', name: 'Qonto main', newName: 'Qonto main' });
    await flushPromises();
    expect(editBank).toHaveBeenCalledWith({ credentials, location: 'qonto', name: 'Qonto main', newName: undefined });

    await banks.setupBank({ credentials, location: 'qonto', mode: 'edit', name: 'Qonto main', newName: 'Renamed' });
    await flushPromises();
    expect(editBank).toHaveBeenLastCalledWith({ credentials, location: 'qonto', name: 'Qonto main', newName: 'Renamed' });
    expect(getBanks).toHaveBeenCalledTimes(7);
    expect(queryAllBankEvents).toHaveBeenCalledOnce();
  });

  describe('answering an authentication request', () => {
    const challenge = { challenge: null, challengeData: null, challengeHtml: null, challengeMimeType: null, primitive: 'otp input' as const, prompt: 'Enter TAN' };

    it('should send only the connection identity, whatever else the caller holds', async () => {
      useBankConnectionsStore().setConnections([connection]);
      answerAuthentication.mockResolvedValue(ok(true));

      const request: BankAuthenticationRequest = { challenge, location: 'qonto', name: 'Qonto main' };
      await useBanks().answerBankAuthentication(request, '123456');

      expect(answerAuthentication).toHaveBeenCalledExactlyOnceWith({ location: 'qonto', name: 'Qonto main', response: '123456' });
    });

    it('should refresh the connection and balances of an existing connection without starting another sync', async () => {
      useBankConnectionsStore().setConnections([connection]);
      answerAuthentication.mockResolvedValue(ok(true));

      await useBanks().answerBankAuthentication({ location: 'qonto', name: 'Qonto main' }, '123456');
      await flushPromises();

      expect(getBanks).toHaveBeenCalledTimes(2);
      expect(queryBankBalances).toHaveBeenCalledOnce();
      expect(queryAllBankEvents).not.toHaveBeenCalled();
      expect(notifyInfo).not.toHaveBeenCalled();
    });

    it('should sync a connection whose setup the answer completed', async () => {
      useBankConnectionsStore().setConnections([connection]);
      answerAuthentication.mockResolvedValue(ok({ historyStartTs: null, success: true }));

      await useBanks().answerBankAuthentication({ location: 'qonto', name: 'Qonto main' }, '123456');
      await flushPromises();

      expect(queryAllBankEvents).toHaveBeenCalledExactlyOnceWith([{ location: 'qonto', name: 'Qonto main' }]);
    });

    it('should hand back a further challenge without refreshing', async () => {
      answerAuthentication.mockResolvedValue(ok(challenge));

      expect(await useBanks().answerBankAuthentication({ location: 'qonto', name: 'Qonto main' })).toEqual(ok(challenge));
      await flushPromises();

      expect(getBanks).not.toHaveBeenCalled();
    });
  });

  it('should send only the credentials that were filled in when editing, so a blank slot keeps its stored value', async () => {
    editBank.mockResolvedValue(ok(true));
    const banks = useBanks();

    await banks.setupBank({
      credentials: { api_key: '', api_secret: '  ' },
      location: 'qonto',
      mode: 'edit',
      name: 'Qonto main',
      newName: 'Renamed',
    });
    expect(editBank).toHaveBeenLastCalledWith({ credentials: {}, location: 'qonto', name: 'Qonto main', newName: 'Renamed' });

    await banks.setupBank({
      credentials: { api_key: '', api_secret: 'new-secret' },
      location: 'qonto',
      mode: 'edit',
      name: 'Qonto main',
      newName: 'Qonto main',
    });
    expect(editBank).toHaveBeenLastCalledWith({ credentials: { api_secret: 'new-secret' }, location: 'qonto', name: 'Qonto main', newName: undefined });
  });

  it('should return the accepted setup and refresh the connections and balances', async () => {
    useBankConnectionsStore().setConnections([connection]);
    const success = { historyStartTs: 1_700_000_000, success: true };
    addBank.mockResolvedValue(ok(success));
    const outcome = await useBanks().setupBank({ credentials: {}, location: 'qonto', mode: 'add', name: 'Qonto main', newName: '' });
    await flushPromises();
    expect(outcome).toEqual(ok(success));
    expect(getBanks).toHaveBeenCalledTimes(3);
    expect(queryBankBalances).toHaveBeenCalledOnce();
    expect(queryAllBankEvents).toHaveBeenCalledWith([{ location: 'qonto', name: 'Qonto main' }]);
    expect(notifyInfo).toHaveBeenCalledOnce();
  });

  it.each([
    ['a refused setup', err<BankSetupError>({ message: 'bank said no', type: 'rejected' })],
    ['an authentication challenge', ok({ challenge: null, challengeData: null, challengeHtml: null, challengeMimeType: null, primitive: 'otp input' as const, prompt: 'Enter TAN' })],
  ])('should hand back %s untouched, without notifying or refreshing', async (_case, answer) => {
    useBankConnectionsStore().setConnections([connection]);
    addBank.mockResolvedValue(answer);
    const outcome = await useBanks().setupBank({ credentials: {}, location: 'qonto', mode: 'add', name: 'x', newName: '' });
    await flushPromises();
    expect(outcome).toEqual(answer);
    expect(notifyError).not.toHaveBeenCalled();
    expect(getBanks).not.toHaveBeenCalled();
    expect(queryBankBalances).not.toHaveBeenCalled();
  });

  it('should notify instead of throwing when removal fails', async () => {
    removeBank.mockRejectedValue(new Error('gone'));
    const banks = useBanks();
    expect(await banks.removeBank(connection)).toBe(false);
    expect(notifyError).toHaveBeenCalledOnce();
  });

  it('should leave balances alone when the backend refuses the removal', async () => {
    useBankConnectionsStore().setConnections([connection]);
    removeBank.mockResolvedValue(false);
    const banks = useBanks();
    expect(await banks.removeBank(connection)).toBe(false);
    await flushPromises();
    expect(queryBankBalances).not.toHaveBeenCalled();
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
