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
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const {
  addBank,
  answerAuthentication,
  cancelAuthentication,
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
  cancelAuthentication: vi.fn(),
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
    cancelAuthentication,
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
  image: null,
  connector: 'qonto',
  maintainer: 'rotki',
  secrets: [{ description: '', label: 'Login', secret: true, slot: 'api_key' }],
  setupNotes: [],
  version: '1.0.0',
};

const connection: BankConnection = {
  bankCode: null,
  displayName: 'Qonto',
  identifier: 'c1',
  connector: 'qonto',
  name: 'Qonto main',
  syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false },
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
    submitTask.mockImplementation(async spec => spec.run({ rerun: false, runTask: async (fn: () => Promise<unknown>) => ok(await fn()) }));
    queryBankBalances.mockResolvedValue({
      aggregate: eurOnTheWire,
      connections: [{ accounts: [], balances: eurOnTheWire, connector: 'qonto', identifier: 'c1', name: 'Qonto main' }],
    });
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

  it('should keep a failed bank or connection listing for the bank pages instead of notifying', async () => {
    const supportedDown = new Error('supported down');
    const connectionsDown = new Error('connections down');
    getSupportedBanks.mockRejectedValue(supportedDown);
    getBanks.mockRejectedValue(connectionsDown);
    const banks = useBanks();

    await banks.refreshSupportedBanks();
    await banks.refreshBankConnections();

    const store = useBankConnectionsStore();
    expect(store.manifestsError).toBe(supportedDown);
    expect(store.connectionsError).toBe(connectionsDown);
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should clear a kept failure once a later listing succeeds', async () => {
    getSupportedBanks.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce([manifest]);
    getBanks.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce([connection]);
    const banks = useBanks();
    await banks.refreshSupportedBanks();
    await banks.refreshBankConnections();

    await banks.refreshSupportedBanks();
    await banks.refreshBankConnections();

    const store = useBankConnectionsStore();
    expect(store.manifestsError).toBeUndefined();
    expect(store.connectionsError).toBeUndefined();
  });

  it('should keep nothing when listing the banks or connections is cancelled, as on a logout', async () => {
    getSupportedBanks.mockRejectedValue(new RequestCancelledError('No live session'));
    getBanks.mockRejectedValue(new RequestCancelledError('No live session'));
    const banks = useBanks();

    await banks.refreshSupportedBanks();
    await banks.refreshBankConnections();

    const store = useBankConnectionsStore();
    expect(store.manifestsError).toBeUndefined();
    expect(store.connectionsError).toBeUndefined();
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should add through PUT and edit through PATCH, dropping an unchanged new name and refreshing after each setup and balance query', async () => {
    addBank.mockResolvedValue(ok({ historyStartTs: null, identifier: 'c1', success: true }));
    editBank.mockResolvedValue(ok(true));
    const banks = useBanks();
    const credentials = { api_key: 'login' };

    await banks.setupBank({ credentials, connector: 'qonto', mode: 'add', name: 'Qonto main', newName: '' });
    await flushPromises();
    expect(addBank).toHaveBeenCalledWith({ credentials, connector: 'qonto', name: 'Qonto main' });

    await banks.setupBank({ connector: 'qonto', credentials, identifier: 'c1', mode: 'edit', name: 'Qonto main', newName: 'Qonto main' });
    await flushPromises();
    expect(editBank).toHaveBeenCalledWith({ credentials, identifier: 'c1', newName: undefined });

    await banks.setupBank({ connector: 'qonto', credentials, identifier: 'c1', mode: 'edit', name: 'Qonto main', newName: 'Renamed' });
    await flushPromises();
    expect(editBank).toHaveBeenLastCalledWith({ credentials, identifier: 'c1', newName: 'Renamed' });
    expect(getBanks).toHaveBeenCalledTimes(6);
    expect(queryAllBankEvents).toHaveBeenCalledOnce();
  });

  it('should refuse an edit without a connection identifier instead of adding a new connection', async () => {
    await expect(useBanks().setupBank({ connector: 'qonto', credentials: {}, mode: 'edit', name: 'Qonto main', newName: 'Qonto main' }))
      .rejects
      .toThrow('editing a bank needs its connection identifier');
    expect(addBank).not.toHaveBeenCalled();
    expect(editBank).not.toHaveBeenCalled();
  });

  describe('answering an authentication request', () => {
    const challenge = { challenge: null, challengeData: null, challengeHtml: null, challengeMimeType: null, primitive: 'otp input' as const, prompt: 'Enter TAN' };

    it('should send only the connection identifier, whatever else the caller holds', async () => {
      useBankConnectionsStore().setConnections([connection]);
      answerAuthentication.mockResolvedValue(ok(true));

      const request: BankAuthenticationRequest = { challenge, connector: 'qonto', identifier: 'c1', name: 'Qonto main' };
      await useBanks().answerBankAuthentication(request, '123456');

      expect(answerAuthentication).toHaveBeenCalledExactlyOnceWith({ identifier: 'c1', response: '123456' });
    });

    it('should refresh the connection and balances of an existing connection without starting another sync', async () => {
      useBankConnectionsStore().setConnections([connection]);
      answerAuthentication.mockResolvedValue(ok(true));

      await useBanks().answerBankAuthentication({ identifier: 'c1' }, '123456');
      await flushPromises();

      expect(getBanks).toHaveBeenCalledTimes(2);
      expect(queryBankBalances).toHaveBeenCalledOnce();
      expect(queryAllBankEvents).not.toHaveBeenCalled();
      expect(notifyInfo).not.toHaveBeenCalled();
    });

    it('should sync a connection whose setup the answer completed', async () => {
      useBankConnectionsStore().setConnections([connection]);
      answerAuthentication.mockResolvedValue(ok({ historyStartTs: null, identifier: 'c1', success: true }));

      await useBanks().answerBankAuthentication({ identifier: 'c1' }, '123456');
      await flushPromises();

      expect(queryAllBankEvents).toHaveBeenCalledExactlyOnceWith([connection]);
    });

    it('should hand back a further challenge and re-read the connections, which now hold it', async () => {
      answerAuthentication.mockResolvedValue(ok(challenge));
      getBanks.mockResolvedValue([connection]);

      expect(await useBanks().answerBankAuthentication({ identifier: 'c1' })).toEqual(ok(challenge));
      await flushPromises();

      expect(getBanks).toHaveBeenCalledOnce();
      expect(queryBankBalances).not.toHaveBeenCalled();
    });
  });

  it('should send only the credentials that were filled in when editing, so a blank slot keeps its stored value', async () => {
    editBank.mockResolvedValue(ok(true));
    const banks = useBanks();

    await banks.setupBank({
      connector: 'qonto',
      credentials: { api_key: '', api_secret: '  ' },
      identifier: 'c1',
      mode: 'edit',
      name: 'Qonto main',
      newName: 'Renamed',
    });
    expect(editBank).toHaveBeenLastCalledWith({ credentials: {}, identifier: 'c1', newName: 'Renamed' });

    await banks.setupBank({
      connector: 'qonto',
      credentials: { api_key: '', api_secret: 'new-secret' },
      identifier: 'c1',
      mode: 'edit',
      name: 'Qonto main',
      newName: 'Qonto main',
    });
    expect(editBank).toHaveBeenLastCalledWith({ credentials: { api_secret: 'new-secret' }, identifier: 'c1', newName: undefined });
  });

  it('should return the accepted setup and refresh the connections and balances', async () => {
    useBankConnectionsStore().setConnections([connection]);
    const success = { historyStartTs: 1_700_000_000, identifier: 'c1', success: true };
    addBank.mockResolvedValue(ok(success));
    const outcome = await useBanks().setupBank({ credentials: {}, connector: 'qonto', mode: 'add', name: 'Qonto main', newName: '' });
    await flushPromises();
    expect(outcome).toEqual(ok(success));
    expect(getBanks).toHaveBeenCalledTimes(2);
    expect(queryBankBalances).toHaveBeenCalledOnce();
    expect(queryAllBankEvents).toHaveBeenCalledWith([connection]);
    expect(notifyInfo).not.toHaveBeenCalled();
  });

  it.each([
    ['a refused setup', err<BankSetupError>({ message: 'bank said no', type: 'rejected' })],
    ['an authentication challenge', ok({ challenge: null, challengeData: null, challengeHtml: null, challengeMimeType: null, primitive: 'otp input' as const, prompt: 'Enter TAN' })],
  ])('should hand back %s untouched, without notifying or refreshing', async (_case, answer) => {
    useBankConnectionsStore().setConnections([connection]);
    addBank.mockResolvedValue(answer);
    const outcome = await useBanks().setupBank({ credentials: {}, connector: 'qonto', mode: 'add', name: 'x', newName: '' });
    await flushPromises();
    expect(outcome).toEqual(answer);
    expect(notifyError).not.toHaveBeenCalled();
    expect(getBanks).not.toHaveBeenCalled();
    expect(queryBankBalances).not.toHaveBeenCalled();
  });

  it('should throw a refused removal for the table to name, without a notification', async () => {
    removeBank.mockRejectedValue(new Error('gone'));
    await expect(useBanks().removeBank(connection)).rejects.toThrow('gone');
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should drop a removed connection\'s balances at once, keeping the others', async () => {
    const dkb = { connector: 'fints', identifier: 'c2', name: 'DKB' };
    useBankConnectionsStore().setConnections([connection]);
    const balances = useBalancesStore();
    balances.bankBalances = [
      { accounts: [], balances: eur, connector: 'qonto', identifier: 'c1', name: 'Qonto main' },
      { accounts: [], balances: eur, ...dkb },
    ];
    removeBank.mockResolvedValue(true);
    queryBankBalances.mockReturnValue(new Promise(() => {}));

    expect(await useBanks().removeBank(dkb)).toBe(true);
    expect(balances.bankBalances.map(({ name }) => name)).toEqual(['Qonto main']);
  });

  it('should leave balances alone when the backend refuses the removal', async () => {
    useBankConnectionsStore().setConnections([connection]);
    removeBank.mockResolvedValue(false);
    const banks = useBanks();
    expect(await banks.removeBank(connection)).toBe(false);
    await flushPromises();
    expect(queryBankBalances).not.toHaveBeenCalled();
  });

  it('should sync the picked connection through the bank events activity, which re-reads the status itself', async () => {
    const side = { ...connection, identifier: 'c2', name: 'Qonto side' };
    const fints = { ...connection, connector: 'fints', displayName: 'FinTS', identifier: 'c3', name: 'ING' };
    useBankConnectionsStore().setConnections([connection, side, fints]);
    const banks = useBanks();
    expect(await banks.syncBanks({ identifier: 'c1' })).toBe(true);
    expect(queryAllBankEvents).toHaveBeenCalledWith([connection]);
    expect(getBanks).not.toHaveBeenCalled();

    await banks.syncBanks({ connector: 'qonto' });
    expect(queryAllBankEvents).toHaveBeenLastCalledWith([connection, side]);

    await banks.syncBanks();
    expect(queryAllBankEvents).toHaveBeenLastCalledWith([connection, side, fints]);
  });

  it('should re-read the connections when there is nothing to sync, since the activity never runs', async () => {
    getBanks.mockResolvedValue([connection]);

    expect(await useBanks().syncBanks({ identifier: 'c1' })).toBe(false);

    expect(queryAllBankEvents).not.toHaveBeenCalled();
    expect(getBanks).toHaveBeenCalledOnce();
    expect(useBankConnectionsStore().connections).toEqual([connection]);
  });

  describe('dropping a setup when its dialog closes', () => {
    it('should drop the setup through the start-over endpoint without syncing anything', async () => {
      cancelAuthentication.mockResolvedValue(true);

      await useBanks().cancelBankSetup({ identifier: 's1' });

      expect(cancelAuthentication).toHaveBeenCalledExactlyOnceWith({ identifier: 's1' });
      expect(queryAllBankEvents).not.toHaveBeenCalled();
    });

    it('should stay quiet when the backend has no such setup, since the next add discards it anyway', async () => {
      cancelAuthentication.mockRejectedValue(new Error('fints bank connection Main does not exist'));

      await expect(useBanks().cancelBankSetup({ identifier: 's1' })).resolves.toBeUndefined();

      expect(notifyError).not.toHaveBeenCalled();
    });
  });

  describe('starting over from a pending TAN', () => {
    it('should drop the challenge, re-read the connections and sync again so the bank sends a fresh one', async () => {
      useBankConnectionsStore().setConnections([connection]);
      cancelAuthentication.mockResolvedValue(true);
      getBanks.mockResolvedValue([connection]);
      queryAllBankEvents.mockResolvedValue([ok(undefined)]);

      await useBanks().startOverAuthentication(connection);

      expect(cancelAuthentication).toHaveBeenCalledExactlyOnceWith({ identifier: 'c1' });
      expect(queryAllBankEvents).toHaveBeenCalledExactlyOnceWith([connection]);
      const [cancelled, reread, synced] = [cancelAuthentication, getBanks, queryAllBankEvents]
        .map(mock => mock.mock.invocationCallOrder[0]);
      expect(cancelled).toBeLessThan(reread);
      expect(reread).toBeLessThan(synced);
    });

    it('should say so and sync nothing when the challenge could not be dropped', async () => {
      useBankConnectionsStore().setConnections([connection]);
      cancelAuthentication.mockRejectedValue(new Error('backend down'));
      getBanks.mockResolvedValue([connection]);

      await useBanks().startOverAuthentication(connection);

      expect(queryAllBankEvents).not.toHaveBeenCalled();
      expect(notifyError).toHaveBeenCalledExactlyOnceWith(
        'bank_settings.errors.start_over_title',
        'bank_settings.errors.start_over_message::backend down, Qonto main',
      );
    });
  });

  it('should report a failed sync as false', async () => {
    useBankConnectionsStore().setConnections([connection]);
    queryAllBankEvents.mockResolvedValue([err(TaskFailed({ message: 'boom' }))]);
    expect(await useBanks().syncBanks()).toBe(false);
  });

  it('should keep bank balances apart from the exchange balances, and drop them without connections', async () => {
    const balances = useBalancesStore();
    balances.exchangeBalances = { kraken: eur };
    const store = useBankConnectionsStore();
    store.setConnections([connection]);
    const banks = useBanks();

    await banks.fetchBankBalances(true);
    expect(queryBankBalances).toHaveBeenCalledWith(true, undefined);
    expect(Object.keys(balances.exchangeBalances)).toEqual(['kraken']);
    expect(balances.bankBalances).toEqual([{
      accounts: [],
      balances: eur,
      connector: 'qonto',
      identifier: 'c1',
      name: 'Qonto main',
    }]);

    store.setConnections([]);
    await banks.fetchBankBalances();
    expect(queryBankBalances).toHaveBeenCalledOnce();
    expect(balances.bankBalances).toEqual([]);
    expect(Object.keys(balances.exchangeBalances)).toEqual(['kraken']);
  });

  it('should bypass the backend cache on a rerun, which would replay a cached failure', async () => {
    useBankConnectionsStore().setConnections([connection]);
    submitTask.mockImplementationOnce(async spec => spec.run({ rerun: true, runTask: async (fn: () => Promise<unknown>) => ok(await fn()) }));

    await useBanks().fetchBankBalances();

    expect(queryBankBalances).toHaveBeenCalledWith(true, undefined);
  });

  it('should refresh one connection without dropping the others', async () => {
    const balances = useBalancesStore();
    const store = useBankConnectionsStore();
    const dkb = { connector: 'fints', identifier: 'c2', name: 'DKB' };
    store.setConnections([connection, { ...connection, ...dkb, displayName: 'FinTS' }]);
    balances.bankBalances = [
      { accounts: [], balances: eur, connector: 'qonto', identifier: 'c1', name: 'Qonto main' },
      { accounts: [], balances: eur, ...dkb },
    ];
    queryBankBalances.mockResolvedValue({
      aggregate: { EUR: { amount: '5', value: '5' } },
      connections: [{ accounts: [], balances: { EUR: { amount: '5', value: '5' } }, ...dkb }],
    });

    await useBanks().fetchBankBalances(true, dkb);

    expect(queryBankBalances).toHaveBeenCalledWith(true, dkb);
    expect(submitTask).toHaveBeenCalledWith(expect.objectContaining({ id: 'bank-balances:c2', lane: 'bank-balances' }));
    expect(balances.bankBalances.map(({ balances, name }) => [name, balances.EUR.amount.toFixed()])).toEqual([
      ['Qonto main', '10'],
      ['DKB', '5'],
    ]);
  });

  it('should keep what a bank last reported when a full refresh leaves it out for a TAN', async () => {
    const balances = useBalancesStore();
    const store = useBankConnectionsStore();
    const dkb = { connector: 'fints', identifier: 'c2', name: 'DKB' };
    store.setConnections([connection, { ...connection, ...dkb, displayName: 'FinTS' }]);
    balances.bankBalances = [
      { accounts: [], balances: eur, connector: 'qonto', identifier: 'c1', name: 'Qonto main' },
      { accounts: [], balances: eur, ...dkb },
    ];
    queryBankBalances.mockResolvedValue({
      aggregate: { EUR: { amount: '5', value: '5' } },
      connections: [{ accounts: [], balances: { EUR: { amount: '5', value: '5' } }, connector: 'qonto', identifier: 'c1', name: 'Qonto main' }],
    });

    await useBanks().fetchBankBalances(true);

    expect(balances.bankBalances.map(({ balances, name }) => [name, balances.EUR.amount.toFixed()])).toEqual([
      ['DKB', '10'],
      ['Qonto main', '5'],
    ]);
  });

  it('should keep the accounts of each bank connection it reads', async () => {
    useBankConnectionsStore().setConnections([connection]);
    queryBankBalances.mockResolvedValue({
      aggregate: eurOnTheWire,
      connections: [{
        accounts: [{ amount: '10', asset: 'EUR', iban: 'DE86601995651153419937', identifier: 'acc', name: 'Main', value: '11' }],
        balances: eurOnTheWire,
        connector: 'qonto',
        identifier: 'c1',
        name: 'Qonto main',
      }],
    });

    await useBanks().fetchBankBalances();

    expect(useBalancesStore().bankBalances[0].accounts).toEqual([
      { amount: bigNumberify(10), asset: 'EUR', iban: 'DE86601995651153419937', identifier: 'acc', name: 'Main', value: bigNumberify(11) },
    ]);
  });
});
