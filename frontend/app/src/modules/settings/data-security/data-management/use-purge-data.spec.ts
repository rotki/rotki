import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { DECENTRALIZED_EXCHANGES, Module, PurgeableOnlyModule } from '@/modules/core/common/modules';
import { Purgeable } from '@/modules/session/purge';
import { usePurgeData } from './use-purge-data';

const {
  allExchanges,
  allTxChainsInfo,
  deleteExchangeData,
  deleteModuleData,
  deleteStakeEvents,
  deleteTransactions,
  purgeData,
  show,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    allExchanges: ref<string[]>(['kraken', 'poloniex']),
    allTxChainsInfo: ref<Array<{ id: string }>>([{ id: 'ethereum' }, { id: 'optimism' }]),
    deleteExchangeData: vi.fn(),
    deleteModuleData: vi.fn(),
    deleteStakeEvents: vi.fn(),
    deleteTransactions: vi.fn(),
    purgeData: vi.fn(),
    show: vi.fn(),
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

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): Record<string, unknown> => ({ deleteStakeEvents, deleteTransactions }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

let scope: ReturnType<typeof effectScope>;

function purge(): ReturnType<typeof usePurgeData> {
  scope = effectScope();
  return scope.run(() => usePurgeData())!;
}

function confirmationMessage(): { message: string; title: string } {
  expect(show).toHaveBeenCalledOnce();
  return show.mock.calls[0][0];
}

async function accept(): Promise<void> {
  await show.mock.calls[0][1]();
}

function everyDeleteCall(): number {
  return deleteTransactions.mock.calls.length
    + deleteModuleData.mock.calls.length
    + deleteExchangeData.mock.calls.length
    + deleteStakeEvents.mock.calls.length;
}

describe('modules/settings/data-security/data-management/usePurgeData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    purgeData.mockImplementation(async (
      _source: Purgeable,
      _value: string,
      deleteData: () => Promise<void>,
    ) => deleteData());
    set(allExchanges, ['kraken', 'poloniex']);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the confirmation gate', () => {
    it('should delete nothing merely because the user pressed purge', () => {
      const { modelSource, showConfirmation } = purge();

      showConfirmation(get(modelSource));

      expect(show).toHaveBeenCalledOnce();
      expect(everyDeleteCall()).toBe(0);
      expect(purgeData).not.toHaveBeenCalled();
    });

    it('should delete nothing when the user never accepts', () => {
      const { modelSource, showConfirmation } = purge();

      showConfirmation(get(modelSource));

      expect(everyDeleteCall()).toBe(0);
    });

    it('should delete once the user accepts', async () => {
      const { showConfirmation } = purge();

      showConfirmation(Purgeable.TRANSACTIONS);
      await accept();

      expect(deleteTransactions).toHaveBeenCalledOnce();
    });
  });

  describe('what each source deletes', () => {
    it('should route transactions to the transaction endpoint and nothing else', async () => {
      const { modelChain, showConfirmation } = purge();
      set(modelChain, 'ethereum');

      showConfirmation(Purgeable.TRANSACTIONS);
      await accept();

      expect(deleteTransactions).toHaveBeenCalledExactlyOnceWith('ethereum');
      expect(everyDeleteCall()).toBe(1);
    });

    it('should route a defi module to the module endpoint and nothing else', async () => {
      const { modelModule, showConfirmation } = purge();
      set(modelModule, Module.LIQUITY);

      showConfirmation(Purgeable.DEFI_MODULES);
      await accept();

      expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(Module.LIQUITY);
      expect(everyDeleteCall()).toBe(1);
    });

    it('should route a centralized exchange to the exchange endpoint and nothing else', async () => {
      const { modelCentralizedExchange, showConfirmation } = purge();
      set(modelCentralizedExchange, 'kraken');

      showConfirmation(Purgeable.CENTRALIZED_EXCHANGES);
      await accept();

      expect(deleteExchangeData).toHaveBeenCalledExactlyOnceWith('kraken', 'all');
      expect(everyDeleteCall()).toBe(1);
    });

    it('should route a decentralized exchange to the module endpoint and nothing else', async () => {
      const { modelDecentralizedExchange, showConfirmation } = purge();
      set(modelDecentralizedExchange, Module.UNISWAP);

      showConfirmation(Purgeable.DECENTRALIZED_EXCHANGES);
      await accept();

      expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(Module.UNISWAP);
      expect(everyDeleteCall()).toBe(1);
    });

    it.each([
      ['a withdrawal', Purgeable.ETH_WITHDRAWAL_EVENT],
      ['a block', Purgeable.ETH_BLOCK_EVENT],
    ])('should route %s event to the stake-event endpoint and nothing else', async (_name, source) => {
      const { showConfirmation } = purge();

      showConfirmation(source);
      await accept();

      expect(deleteStakeEvents).toHaveBeenCalledExactlyOnceWith(source);
      expect(everyDeleteCall()).toBe(1);
    });
  });

  describe('what it sends for a narrowed selection', () => {
    it('should send the selected data type rather than always purging every kind', async () => {
      const { modelCentralizedExchange, modelCentralizedExchangeDataType, showConfirmation } = purge();
      set(modelCentralizedExchange, 'kraken');
      set(modelCentralizedExchangeDataType, 'trades');

      showConfirmation(Purgeable.CENTRALIZED_EXCHANGES);
      await accept();

      expect(deleteExchangeData).toHaveBeenCalledWith('kraken', 'trades');
    });

    it('should send an empty chain, meaning all of them, when none was picked', async () => {
      const { showConfirmation } = purge();

      showConfirmation(Purgeable.TRANSACTIONS);
      await accept();

      expect(deleteTransactions).toHaveBeenCalledWith('');
    });

    it('should purge every decentralized exchange when none was picked', async () => {
      const { showConfirmation } = purge();

      showConfirmation(Purgeable.DECENTRALIZED_EXCHANGES);
      await accept();

      expect(deleteModuleData).toHaveBeenCalledTimes(DECENTRALIZED_EXCHANGES.length);
      expect(deleteModuleData.mock.calls.map(([module]) => module)).toEqual(DECENTRALIZED_EXCHANGES);
    });

    it('should send null for a module value it does not recognise, rather than the raw string', async () => {
      const { modelModule, showConfirmation } = purge();
      set(modelModule, 'not-a-module');

      showConfirmation(Purgeable.DEFI_MODULES);
      await accept();

      expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(null);
    });

    it('should delete nothing for a source it does not recognise, rather than a broader purge', async () => {
      const { showConfirmation } = purge();

      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the branch is defensive, so the only way to reach it is a value the enum forbids
      showConfirmation('not_a_purgeable_source' as Purgeable);
      await accept();

      expect(everyDeleteCall()).toBe(0);
    });

    it('should delete nothing for a decentralized value it does not recognise', async () => {
      const { modelDecentralizedExchange, showConfirmation } = purge();
      set(modelDecentralizedExchange, 'not-a-module');

      showConfirmation(Purgeable.DECENTRALIZED_EXCHANGES);
      await accept();

      expect(everyDeleteCall()).toBe(0);
    });
  });

  describe('the purge activity', () => {
    it('should run an ordinary purge through the activity so the caches follow', async () => {
      const { modelChain, showConfirmation } = purge();
      set(modelChain, 'ethereum');

      showConfirmation(Purgeable.TRANSACTIONS);
      await accept();

      expect(purgeData).toHaveBeenCalledOnce();
      expect(purgeData.mock.calls[0][0]).toBe(Purgeable.TRANSACTIONS);
      expect(purgeData.mock.calls[0][1]).toBe('ethereum');
    });

    it('should delete a purgeable-only module directly, since it has no cache to invalidate', async () => {
      const { modelModule, showConfirmation } = purge();
      set(modelModule, PurgeableOnlyModule.LOOPRING);

      showConfirmation(Purgeable.DEFI_MODULES);
      await accept();

      expect(purgeData).not.toHaveBeenCalled();
      expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(PurgeableOnlyModule.LOOPRING);
    });

    it.each(Object.values(PurgeableOnlyModule))(
      'should purge only %s, never every module, when it is the selection',
      async (module) => {
        const { modelModule, showConfirmation } = purge();
        set(modelModule, module);

        showConfirmation(Purgeable.DEFI_MODULES);
        await accept();

        expect(deleteModuleData).toHaveBeenCalledExactlyOnceWith(module);
        expect(deleteModuleData).not.toHaveBeenCalledWith(null);
      },
    );
  });

  describe('what the confirmation says', () => {
    it('should warn about transactions in their own words, not the generic message', () => {
      const { showConfirmation } = purge();

      showConfirmation(Purgeable.TRANSACTIONS);

      expect(confirmationMessage().message).toBe('data_management.purge_data.transaction_purge_confirm.message');
    });

    it('should name the selection when one was made', () => {
      const { modelCentralizedExchange, showConfirmation } = purge();
      set(modelCentralizedExchange, 'kraken');

      showConfirmation(Purgeable.CENTRALIZED_EXCHANGES);

      expect(confirmationMessage().message).toContain('data_management.purge_data.confirm.message');
      expect(confirmationMessage().message).toContain('Kraken');
    });

    it('should say all of them when nothing narrows the purge', () => {
      const { showConfirmation } = purge();

      showConfirmation(Purgeable.DEFI_MODULES);

      expect(confirmationMessage().message).toContain('data_management.purge_data.confirm.message_all');
    });

    it('should add the retention warning for an exchange that cannot serve its full history', () => {
      const { modelCentralizedExchange, showConfirmation } = purge();
      set(modelCentralizedExchange, 'poloniex');

      showConfirmation(Purgeable.CENTRALIZED_EXCHANGES);

      expect(confirmationMessage().message).toContain('exchange_trade_history_warning');
      expect(confirmationMessage().message).toContain('180');
    });

    it('should not add the retention warning for an exchange that can', () => {
      const { modelCentralizedExchange, showConfirmation } = purge();
      set(modelCentralizedExchange, 'kraken');

      showConfirmation(Purgeable.CENTRALIZED_EXCHANGES);

      expect(confirmationMessage().message).not.toContain('exchange_trade_history_warning');
    });
  });

  describe('what it offers the form', () => {
    it('should offer every purgeable source', () => {
      expect(purge().purgeable.map(item => item.id)).toEqual([
        Purgeable.CENTRALIZED_EXCHANGES,
        Purgeable.DECENTRALIZED_EXCHANGES,
        Purgeable.DEFI_MODULES,
        Purgeable.TRANSACTIONS,
        Purgeable.ETH_WITHDRAWAL_EVENT,
        Purgeable.ETH_BLOCK_EVENT,
      ]);
    });

    it('should offer the purgeable-only modules alongside the ordinary ones', () => {
      const { purgeableModules } = purge();

      expect(purgeableModules).toContain(Module.LIQUITY);
      expect(purgeableModules).toContain(PurgeableOnlyModule.LOOPRING);
    });

    it('should offer every slice of exchange data, with all of it first', () => {
      const options = get(purge().centralizedExchangePurgeTypeOptions);

      expect(options.map(option => option.id)).toEqual(['all', 'trades', 'asset_movements', 'other']);
    });

    it('should offer the chains that can hold transactions', () => {
      expect(get(purge().chainsSelection)).toEqual(['ethereum', 'optimism']);
    });

    it('should start on transactions, the least destructive default', () => {
      expect(get(purge().modelSource)).toBe(Purgeable.TRANSACTIONS);
    });
  });
});
