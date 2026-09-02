import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import { pluralize, toSentenceCase } from '@rotki/common';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { isOfEnum } from '@/modules/core/common/helpers/is-of-enum';
import { DECENTRALIZED_EXCHANGES, Module, type PurgeableModule, PurgeableOnlyModule } from '@/modules/core/common/modules';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { Purgeable } from '@/modules/session/purge';
import { useCacheClear } from '@/modules/session/use-cache-clear';
import { useSessionPurge } from '@/modules/session/use-purge';

/** Which slice of a centralized exchange's data a purge removes; `all` takes every kind. */
type CentralizedExchangePurgeType = 'all' | 'trades' | 'asset_movements' | 'other';

/**
 * Exchanges that serve only a limited window of trade history, keyed by the days they retain.
 *
 * @remarks
 * Purging one of these is not fully reversible: re-querying cannot recover trades older than the
 * window, so the confirmation grows an extra warning naming the limit. An exchange absent from
 * this record is assumed to serve its full history.
 */
const EXCHANGE_TRADE_HISTORY_LIMITS: Record<string, number> = {
  poloniex: 180,
};

/**
 * The purge surface, ready to bind. Every `model*` ref is writable for `v-model`; the rest is
 * read-only state or an action.
 */
interface UsePurgeDataReturn {
  /** Options for the centralized-exchange data-type picker, in display order. */
  centralizedExchangePurgeTypeOptions: ComputedRef<Array<{ id: CentralizedExchangePurgeType; text: string }>>;
  /** Ids of every chain that can hold transactions, for the chain picker. */
  chainsSelection: ComputedRef<string[]>;
  /** Every exchange the user has configured, for the centralized-exchange picker. */
  exchanges: Readonly<Ref<string[]>>;
  /** Empty means every centralized exchange. */
  modelCentralizedExchange: Ref<string>;
  modelCentralizedExchangeDataType: Ref<CentralizedExchangePurgeType>;
  /** Empty means every chain. */
  modelChain: Ref<string>;
  /** Empty means every decentralized exchange. */
  modelDecentralizedExchange: Ref<string>;
  /** Empty means every module. */
  modelModule: Ref<string>;
  /** What the purge button acts on; selects which picker the form shows. */
  modelSource: Ref<Purgeable>;
  /** True while a purge is in flight, so the form can lock itself. */
  pending: Readonly<Ref<boolean>>;
  /** Every purgeable source with its label, and the ref holding its narrowing selection. */
  purgeable: Array<{ id: Purgeable; text: string; value?: Ref<string> }>;
  /** Modules offered to the module picker, including the purgeable-only ones. */
  purgeableModules: PurgeableModule[];
  /**
   * Opens the confirmation for `source`, and purges only once the user accepts.
   *
   * @remarks
   * Nothing is deleted by calling this. The destructive call happens in the confirmation's accept
   * handler, against the selection held at the moment the user accepts.
   */
  showConfirmation: (source: Purgeable) => void;
  /** Outcome of the last purge, cleared a few seconds after a success. */
  status: DeepReadonly<Ref<BaseMessage | null>>;
}

/**
 * Drives the "purge data" settings row: what can be purged, what the user narrowed it to, and the
 * deletion each choice maps to.
 *
 * @remarks
 * Every source routes to its own endpoint, and an unrecognised one deletes nothing rather than
 * falling back to a broader purge. A purgeable-only module is deleted directly instead of through
 * the purge activity, having no derived cache for a `staleAfter` edge to hang off.
 *
 * @returns the form's bindings plus {@link UsePurgeDataReturn.showConfirmation}, which is the only
 * way this composable deletes anything
 */
export function usePurgeData(): UsePurgeDataReturn {
  const isModule = isOfEnum(Module);
  const purgeableOnlyModules: string[] = Object.values(PurgeableOnlyModule);
  const purgeableModules: PurgeableModule[] = [...Object.values(Module), ...Object.values(PurgeableOnlyModule)];

  const isPurgeableModule = (value: string): value is PurgeableModule =>
    isModule(value) || purgeableOnlyModules.includes(value);

  const { t } = useI18n({ useScope: 'global' });

  const { allExchanges } = storeToRefs(useLocationStore());
  const { allTxChainsInfo } = useSupportedChains();

  const { purgeData } = useSessionPurge();
  const { deleteModuleData } = useBlockchainBalancesApi();
  const { deleteStakeEvents, deleteTransactions } = useHistoryEventsApi();
  const { deleteExchangeData } = useExchangeApi();

  const modelSource = shallowRef<Purgeable>(Purgeable.TRANSACTIONS);
  const modelCentralizedExchange = shallowRef<string>('');
  const modelCentralizedExchangeDataType = shallowRef<CentralizedExchangePurgeType>('all');
  const modelDecentralizedExchange = shallowRef<string>('');
  const modelChain = shallowRef<string>('');
  const modelModule = shallowRef<string>('');

  const centralizedExchangePurgeTypeOptions = computed<Array<{ id: CentralizedExchangePurgeType; text: string }>>(() => [
    { id: 'all', text: 'All' },
    { id: 'trades', text: 'Trades' },
    { id: 'asset_movements', text: 'Deposits / Withdrawals' },
    { id: 'other', text: 'Other events' },
  ]);

  const purgeable = [
    {
      id: Purgeable.CENTRALIZED_EXCHANGES,
      text: t('purge_selector.centralized_exchange'),
      value: modelCentralizedExchange,
    },
    {
      id: Purgeable.DECENTRALIZED_EXCHANGES,
      text: t('purge_selector.decentralized_exchange'),
      value: modelDecentralizedExchange,
    },
    {
      id: Purgeable.DEFI_MODULES,
      text: t('purge_selector.defi_module'),
      value: modelModule,
    },
    {
      id: Purgeable.TRANSACTIONS,
      text: t('purge_selector.transactions'),
      value: modelChain,
    },
    {
      id: Purgeable.ETH_WITHDRAWAL_EVENT,
      text: t('purge_selector.eth_withdrawals'),
    },
    {
      id: Purgeable.ETH_BLOCK_EVENT,
      text: t('purge_selector.eth_block'),
    },
  ];

  function selectedValue(source: Purgeable): string {
    const valueRef = purgeable.find(({ id }) => id === source)?.value;
    return valueRef ? get(valueRef) : '';
  }

  async function deleteSourceData(source: Purgeable, value: string): Promise<void> {
    if (source === Purgeable.TRANSACTIONS) {
      await deleteTransactions(value);
      return;
    }

    if (source === Purgeable.DEFI_MODULES) {
      await deleteModuleData(isPurgeableModule(value) ? value : null);
      return;
    }

    if (source === Purgeable.CENTRALIZED_EXCHANGES) {
      await deleteExchangeData(value, get(modelCentralizedExchangeDataType));
      return;
    }

    if (source === Purgeable.DECENTRALIZED_EXCHANGES) {
      if (!value) {
        await Promise.all(DECENTRALIZED_EXCHANGES.map(deleteModuleData));
        return;
      }
      if (isModule(value))
        await deleteModuleData(value);
      return;
    }

    if ([Purgeable.ETH_WITHDRAWAL_EVENT, Purgeable.ETH_BLOCK_EVENT].includes(source))
      await deleteStakeEvents(source);
  }

  async function purgeSource(source: Purgeable): Promise<void> {
    const value = selectedValue(source);

    if (purgeableOnlyModules.includes(value)) {
      await deleteSourceData(source, value);
      return;
    }

    await purgeData(source, value, async () => deleteSourceData(source, value));
  }

  function confirmText(textSource: string, source: Purgeable): { message: string; title: string } {
    const value = selectedValue(source);

    let message = '';
    if (source === Purgeable.TRANSACTIONS) {
      message = t('data_management.purge_data.transaction_purge_confirm.message');
    }
    else if (value) {
      message = t('data_management.purge_data.confirm.message', {
        source: textSource,
        value: toSentenceCase(value),
      });
    }
    else {
      message = t('data_management.purge_data.confirm.message_all', {
        source: pluralize(textSource),
      });
    }

    if (source === Purgeable.CENTRALIZED_EXCHANGES && value && value in EXCHANGE_TRADE_HISTORY_LIMITS) {
      message += `\n\n${t('data_management.purge_data.confirm.exchange_trade_history_warning', {
        days: EXCHANGE_TRADE_HISTORY_LIMITS[value],
        exchange: toSentenceCase(value),
      })}`;
    }

    return {
      message,
      title: t('data_management.purge_data.confirm.title'),
    };
  }

  const { pending, showConfirmation, status } = useCacheClear<Purgeable>(
    purgeable,
    purgeSource,
    (source: string) => ({
      error: t('data_management.purge_data.error', { source }),
      success: t('data_management.purge_data.success', { source }),
    }),
    confirmText,
  );

  return {
    centralizedExchangePurgeTypeOptions,
    chainsSelection: useArrayMap(allTxChainsInfo, item => item.id),
    exchanges: allExchanges,
    modelCentralizedExchange,
    modelCentralizedExchangeDataType,
    modelChain,
    modelDecentralizedExchange,
    modelModule,
    modelSource,
    pending,
    purgeable,
    purgeableModules,
    showConfirmation,
    status,
  };
}
