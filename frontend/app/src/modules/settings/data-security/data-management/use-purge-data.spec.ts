import { invalid } from '@test/utils/invalid';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, nextTick } from 'vue';
import { DECENTRALIZED_EXCHANGES, Module, PurgeableOnlyModule } from '@/modules/core/common/modules';
import { Purgeable } from '@/modules/session/purge';
import { usePurgeData } from './use-purge-data';

const {
  allExchanges,
  allTxChainsInfo,
  deleteExchangeData,
  deleteCsvImportedEvents,
  deleteModuleData,
  deleteStakeEvents,
  deleteTransactions,
  fetchCsvImportedEventsSummary,
  purgeData,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    allExchanges: ref<string[]>(['kraken', 'poloniex']),
    allTxChainsInfo: ref<Array<{ id: string }>>([{ id: 'ethereum' }, { id: 'optimism' }]),
    deleteExchangeData: vi.fn(),
    deleteCsvImportedEvents: vi.fn(),
    deleteModuleData: vi.fn(),
    deleteStakeEvents: vi.fn(),
    deleteTransactions: vi.fn(),
    fetchCsvImportedEventsSummary: vi.fn(),
    purgeData: vi.fn(),
  };
});

vi.mock('@/modules/core/common/use-location-store', () => ({
  useLocationStore: (): Record<string, unknown> => ({ allExchanges }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({ allTxChainsInfo }),
}));

vi.mock('@/modules/session/use-purge', () => ({
  useSessionPurge: (): Record<string, unknown> => ({ purgeData }),
}));

vi.mock('@/modules/balances/api/use-blockchain-balances-api', () => ({
  useBlockchainBalancesApi: (): Record<string, unknown> => ({ deleteModuleData }),
}));

vi.mock('@/modules/balances/api/use-exchange-api', () => ({
  useExchangeApi: (): Record<string, unknown> => ({ deleteExchangeData }),
}));

vi.mock('@/modules/history/api/events/use-csv-imported-events-api', () => ({
  useCsvImportedEventsApi: (): Record<string, unknown> => ({
    deleteCsvImportedEvents,
    fetchCsvImportedEventsSummary,
  }),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): Record<string, unknown> => ({
    deleteStakeEvents,
    deleteTransactions,
  }),
}));

let scope: ReturnType<typeof effectScope>;

function createPurgeData(): ReturnType<typeof usePurgeData> {
  scope = effectScope();
  return scope.run(() => usePurgeData())!;
}

function everyDeleteCall(): number {
  return deleteTransactions.mock.calls.length
    + deleteModuleData.mock.calls.length
    + deleteExchangeData.mock.calls.length
    + deleteCsvImportedEvents.mock.calls.length
    + deleteStakeEvents.mock.calls.length;
}

describe('modules/settings/data-security/data-management/usePurgeData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    purgeData.mockImplementation(async (
      _source: Purgeable,
      _value: string,
      deleteData: () => Promise<void>,
    ) => {
      await deleteData();
      return true;
    });
    set(allExchanges, ['kraken', 'poloniex']);
    fetchCsvImportedEventsSummary.mockResolvedValue([
      { customizedEventsCount: 2, eventsCount: 3, location: 'binance' },
      { customizedEventsCount: 0, eventsCount: 1, location: 'kraken' },
    ]);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('what each source deletes', () => {
    it('should route transactions to the transaction endpoint and nothing else', async () => {
      const { modelChain, purge } = createPurgeData();
      set(modelChain, 'ethereum');

      await purge(Purgeable.TRANSACTIONS);

      expect(deleteTransactions).toHaveBeenCalledExactlyOnceWith('ethereum');
      expect(everyDeleteCall()).toBe(1);
    });

    it('should route a defi module to the module endpoint and nothing else', async () => {
      const { modelModule, purge } = createPurgeData();
      set(modelModule, Module.LIQUITY);

      await purge(Purgeable.DEFI_MODULES);

      expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(Module.LIQUITY);
      expect(everyDeleteCall()).toBe(1);
    });

    it('should route a centralized exchange to the exchange endpoint and nothing else', async () => {
      const { modelCentralizedExchange, purge } = createPurgeData();
      set(modelCentralizedExchange, 'kraken');

      await purge(Purgeable.CENTRALIZED_EXCHANGES);

      expect(deleteExchangeData).toHaveBeenCalledExactlyOnceWith('kraken', 'all');
      expect(everyDeleteCall()).toBe(1);
    });

    it('should route CSV imports to their endpoint and refresh the available locations', async () => {
      const { modelCsvImportLocation, purge } = createPurgeData();
      set(modelCsvImportLocation, 'kraken');
      await flushPromises();
      fetchCsvImportedEventsSummary.mockClear();

      await purge(Purgeable.CSV_IMPORTS);

      expect(deleteCsvImportedEvents).toHaveBeenCalledExactlyOnceWith('kraken');
      expect(fetchCsvImportedEventsSummary).toHaveBeenCalledOnce();
    });

    it('should run a CSV purge at a location named like a purgeable-only module through the activity', async () => {
      const { modelCsvImportLocation, purge } = createPurgeData();
      set(modelCsvImportLocation, PurgeableOnlyModule.LOOPRING);

      await purge(Purgeable.CSV_IMPORTS);

      expect(purgeData).toHaveBeenCalledOnce();
      expect(deleteCsvImportedEvents).toHaveBeenCalledExactlyOnceWith(PurgeableOnlyModule.LOOPRING);
    });

    it('should route a decentralized exchange to the module endpoint and nothing else', async () => {
      const { modelDecentralizedExchange, purge } = createPurgeData();
      set(modelDecentralizedExchange, Module.UNISWAP);

      await purge(Purgeable.DECENTRALIZED_EXCHANGES);

      expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(Module.UNISWAP);
      expect(everyDeleteCall()).toBe(1);
    });

    it.each([
      ['a withdrawal', Purgeable.ETH_WITHDRAWAL_EVENT],
      ['a block', Purgeable.ETH_BLOCK_EVENT],
    ])('should route %s event to the stake-event endpoint and nothing else', async (_name, source) => {
      const { purge } = createPurgeData();

      await purge(source);

      expect(deleteStakeEvents).toHaveBeenCalledExactlyOnceWith(source);
      expect(everyDeleteCall()).toBe(1);
    });
  });

  describe('what it sends for a narrowed selection', () => {
    it('should send the selected data type rather than always purging every kind', async () => {
      const { modelCentralizedExchange, modelCentralizedExchangeDataType, purge } = createPurgeData();
      set(modelCentralizedExchange, 'kraken');
      set(modelCentralizedExchangeDataType, 'trades');

      await purge(Purgeable.CENTRALIZED_EXCHANGES);

      expect(deleteExchangeData).toHaveBeenCalledWith('kraken', 'trades');
    });

    it('should send an empty chain, meaning all of them, when none was picked', async () => {
      const { purge } = createPurgeData();

      await purge(Purgeable.TRANSACTIONS);

      expect(deleteTransactions).toHaveBeenCalledWith('');
    });

    it('should purge every decentralized exchange when none was picked', async () => {
      const { purge } = createPurgeData();

      await purge(Purgeable.DECENTRALIZED_EXCHANGES);

      expect(deleteModuleData).toHaveBeenCalledTimes(DECENTRALIZED_EXCHANGES.length);
      expect(deleteModuleData.mock.calls.map(([module]) => module)).toEqual(DECENTRALIZED_EXCHANGES);
    });

    it('should send null for a module value it does not recognise, rather than the raw string', async () => {
      const { modelModule, purge } = createPurgeData();
      set(modelModule, 'not-a-module');

      await purge(Purgeable.DEFI_MODULES);

      expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(null);
    });

    it('should delete nothing for a source it does not recognise, rather than a broader purge', async () => {
      const { purge } = createPurgeData();

      await purge(invalid<Purgeable>('not_a_purgeable_source'));

      expect(everyDeleteCall()).toBe(0);
    });

    it('should delete nothing for a decentralized value it does not recognise', async () => {
      const { modelDecentralizedExchange, purge } = createPurgeData();
      set(modelDecentralizedExchange, 'not-a-module');

      await purge(Purgeable.DECENTRALIZED_EXCHANGES);

      expect(everyDeleteCall()).toBe(0);
    });
  });

  describe('the purge activity', () => {
    it('should run an ordinary purge through the activity so the caches follow', async () => {
      const { modelChain, purge } = createPurgeData();
      set(modelChain, 'ethereum');

      await purge(Purgeable.TRANSACTIONS);

      expect(purgeData).toHaveBeenCalledOnce();
      expect(purgeData.mock.calls[0][0]).toBe(Purgeable.TRANSACTIONS);
      expect(purgeData.mock.calls[0][1]).toBe('ethereum');
    });

    it('should delete a purgeable-only module directly, since it has no cache to invalidate', async () => {
      const { modelModule, purge } = createPurgeData();
      set(modelModule, PurgeableOnlyModule.LOOPRING);

      await purge(Purgeable.DEFI_MODULES);

      expect(purgeData).not.toHaveBeenCalled();
      expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(PurgeableOnlyModule.LOOPRING);
    });

    it.each(Object.values(PurgeableOnlyModule))(
      'should purge only %s, never every module, when it is the selection',
      async (module) => {
        const { modelModule, purge } = createPurgeData();
        set(modelModule, module);

        await purge(Purgeable.DEFI_MODULES);

        expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(module);
        expect(deleteModuleData).not.toHaveBeenCalledWith(null);
      },
    );
  });

  describe('what the purge button asks', () => {
    it('should ask in the error tone, with an accept button that names the purge', () => {
      const { modelSource, purgeQuestion } = createPurgeData();
      set(modelSource, Purgeable.TRANSACTIONS);

      expect(get(purgeQuestion)).toMatchObject({ confirmLabel: 'purge_selector.tooltip', tone: 'error' });
    });

    it('should warn about transactions in their own words, not the generic message', () => {
      const { modelSource, purgeQuestion } = createPurgeData();
      set(modelSource, Purgeable.TRANSACTIONS);

      expect(get(purgeQuestion).message).toBe('data_management.purge_data.transaction_purge_confirm.message');
    });

    it('should name the selection when one was made', () => {
      const { modelCentralizedExchange, modelSource, purgeQuestion } = createPurgeData();
      set(modelCentralizedExchange, 'kraken');
      set(modelSource, Purgeable.CENTRALIZED_EXCHANGES);

      expect(get(purgeQuestion).message).toContain('data_management.purge_data.confirm.message');
      expect(get(purgeQuestion).message).toContain('Kraken');
    });

    it('should say all of them when nothing narrows the purge', () => {
      const { modelSource, purgeQuestion } = createPurgeData();
      set(modelSource, Purgeable.DEFI_MODULES);

      expect(get(purgeQuestion).message).toContain('data_management.purge_data.confirm.message_all');
    });

    it('should add the retention warning, as a second paragraph, for an exchange that cannot serve its full history', () => {
      const { modelCentralizedExchange, modelSource, purgeQuestion } = createPurgeData();
      set(modelCentralizedExchange, 'poloniex');
      set(modelSource, Purgeable.CENTRALIZED_EXCHANGES);

      expect(get(purgeQuestion).message).toMatch(/^data_management\.purge_data\.confirm\.message.*\n\n.*exchange_trade_history_warning/s);
      expect(get(purgeQuestion).message).toContain('180');
    });

    it('should warn about edited CSV events and Binance API history', async () => {
      const { modelCsvImportLocation, modelSource, purgeQuestion } = createPurgeData();
      set(modelCsvImportLocation, 'binance');
      set(modelSource, Purgeable.CSV_IMPORTS);
      await flushPromises();

      expect(get(purgeQuestion).message).toContain('customized_warning');
      expect(get(purgeQuestion).message).toContain('binance_warning');
      expect(get(purgeQuestion).message).toContain('version_warning');
    });

    it('should bring the CSV counts it quotes up to date when CSV imports are picked, locking the button meanwhile', async () => {
      const { modelSource, pending } = createPurgeData();
      await flushPromises();
      fetchCsvImportedEventsSummary.mockClear();

      set(modelSource, Purgeable.CSV_IMPORTS);
      await nextTick();

      expect(fetchCsvImportedEventsSummary).toHaveBeenCalledOnce();
      expect(get(pending)).toBe(true);
      await flushPromises();
      expect(get(pending)).toBe(false);
    });

    it('should not add the retention warning for an exchange that can', () => {
      const { modelCentralizedExchange, modelSource, purgeQuestion } = createPurgeData();
      set(modelCentralizedExchange, 'kraken');
      set(modelSource, Purgeable.CENTRALIZED_EXCHANGES);

      expect(get(purgeQuestion).message).not.toContain('exchange_trade_history_warning');
    });
  });

  describe('what it offers the form', () => {
    it('should offer every purgeable source', () => {
      expect(createPurgeData().purgeable.map(item => item.id)).toEqual([
        Purgeable.CENTRALIZED_EXCHANGES,
        Purgeable.DECENTRALIZED_EXCHANGES,
        Purgeable.CSV_IMPORTS,
        Purgeable.DEFI_MODULES,
        Purgeable.TRANSACTIONS,
        Purgeable.ETH_WITHDRAWAL_EVENT,
        Purgeable.ETH_BLOCK_EVENT,
      ]);
    });

    it('should offer the purgeable-only modules alongside the ordinary ones', () => {
      const { purgeableModules } = createPurgeData();

      expect(purgeableModules).toContain(Module.LIQUITY);
      expect(purgeableModules).toContain(PurgeableOnlyModule.LOOPRING);
    });

    it('should offer every slice of exchange data, with all of it first', () => {
      const options = get(createPurgeData().centralizedExchangePurgeTypeOptions);

      expect(options.map(option => option.id)).toEqual(['all', 'trades', 'asset_movements', 'other']);
    });

    it('should offer the chains that can hold transactions', () => {
      expect(get(createPurgeData().chainsSelection)).toEqual(['ethereum', 'optimism']);
    });

    it('should offer only locations containing CSV-imported events', async () => {
      const { csvImportLocations } = createPurgeData();
      await flushPromises();

      expect(get(csvImportLocations)).toEqual(['binance', 'kraken']);
    });

    it('should start on transactions, the least destructive default', () => {
      expect(get(createPurgeData().modelSource)).toBe(Purgeable.TRANSACTIONS);
    });
  });
});
