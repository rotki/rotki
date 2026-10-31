import type { ComputedRef, ModelRef, Ref } from 'vue';
import type { EvmHistoryEvent, EvmSwapEvent, SolanaEvent, SolanaSwapEvent, SwapEvent } from '@/modules/history/events/schemas';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType, toSnakeCase } from '@rotki/common';
import { generateUUID } from '@shared/utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { collectPriceIntents } from '@/modules/history/management/forms/price-intent';
import { type AddPayload, emptySwapForm, type SwapFormState, swapIdentifiers, type SwapKind, swapSchema, swapServerErrorPaths, swapStateForGroupAdd, swapStateFromEvents, switchSwapKind, toSwapEditPayload, toSwapPayload } from '@/modules/history/management/forms/swap-event-form';
import { emptySubEvent, SUB_EVENT_PRICE_INTENT_KEYS } from '@/modules/history/management/forms/swap/swap-sub-event';
import { useFeeRows } from '@/modules/history/management/forms/swap/use-fee-rows';
import { useEvmTxAutoFill } from '@/modules/history/management/forms/use-evm-tx-lookup';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';

export type SwapFormData = StandaloneEventData<EvmHistoryEvent | SolanaEvent> | GroupEventData<SwapEvent | EvmSwapEvent | SolanaSwapEvent>;

interface UseSwapEventFormOptions {
  /** The dialog's data: a new swap, one added into a transaction, or a group being edited. */
  readonly data: () => SwapFormData;
  /** The entry type picked above the form, which the form's kind follows. */
  readonly entryType: () => SwapKind;
  /** The dialog's `prompt-on-close` flag, kept in step with the form being dirty. */
  readonly stateUpdated: ModelRef<boolean>;
}

interface UseSwapEventFormReturn {
  readonly form: ReturnType<typeof useHistoryEventForm<SwapFormState, AddPayload, ReturnType<typeof toSwapEditPayload>>>['form'];
  readonly save: () => Promise<boolean>;
  readonly isEvm: ComputedRef<boolean>;
  readonly isSolana: ComputedRef<boolean>;
  readonly isPlain: ComputedRef<boolean>;
  /** The locations to pick from: an EVM swap's chains, or every location for the other kinds. */
  readonly locations: ComputedRef<string[]>;
  readonly lookupLoading: Readonly<Ref<boolean>>;
  readonly lookupCanRetry: Readonly<Ref<boolean>>;
  readonly lookupHint: ComputedRef<string>;
  readonly retryLookup: () => Promise<void>;
}

/**
 * The swap form's behaviour, for the three swap entry types.
 *
 * @remarks
 * The form seeds from the dialog's data, and follows the entry type picked above it by switching
 * the kind in place: a switch counts as an edit, so it changes the state rather than reseeding.
 * Only an EVM swap being added looks its transaction up as it is typed.
 */
export function useSwapEventForm({ data, entryType, stateUpdated }: UseSwapEventFormOptions): UseSwapEventFormReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { txChainsToLocation } = useSupportedChains();

  /** Shared with the transaction lookup, which reports its failures as field errors too. */
  const errorMessages = ref<Record<string, string[]>>({});

  const { form, save, seed } = useHistoryEventForm({
    errorMessages,
    initial: () => emptySwapForm(entryType()),
    priceIntentKeys: SUB_EVENT_PRICE_INTENT_KEYS,
    priceIntents: state => collectPriceIntents(state.spend, state.receive, state.fee),
    schema: swapSchema(),
    serverErrorPaths: errors => swapServerErrorPaths(entryType(), errors),
    stateUpdated,
    toEditPayload: toSwapEditPayload,
    transform: state => toSwapPayload(state, generateUUID),
  });

  const { state } = form;

  const isEvm = computed<boolean>(() => state.kind === HistoryEventEntryType.EVM_SWAP_EVENT);
  const isSolana = computed<boolean>(() => state.kind === HistoryEventEntryType.SOLANA_SWAP_EVENT);
  const isPlain = computed<boolean>(() => state.kind === HistoryEventEntryType.SWAP_EVENT);

  const {
    canRetry: lookupCanRetry,
    loading: lookupLoading,
    needsRelatedAddress,
    reset: resetLookup,
    retry: retryLookup,
  } = useEvmTxAutoFill({
    enabled: () => data().type === 'add' && get(isEvm),
    errorFields: { relatedAddress: 'txRef', txHash: 'txRef' },
    errorMessages,
    evmChain: () => toSnakeCase(state.location),
    onResolved: (result) => {
      state.timestamp = result.timestamp * 1000;
    },
    relatedAddress: () => state.spend[0]?.locationLabel ?? '',
    txHash: () => state.txRef,
  });

  const locations = computed<string[]>(() => (get(isEvm) ? get(txChainsToLocation) : []));

  const lookupHint = computed<string>(() => {
    if (get(lookupLoading))
      return t('actions.evm_tx_lookup.loading');
    if (get(needsRelatedAddress))
      return t('actions.evm_tx_lookup.needs_related_address_swap');
    return '';
  });

  function seedFrom(current: SwapFormData): void {
    resetLookup();
    if (current.type === 'group-add')
      seed(swapStateForGroupAdd(entryType(), current.group, current.nextSequenceId.toString()));
    else if (current.type === 'edit-group')
      seed(swapStateFromEvents(current.eventsInGroup), swapIdentifiers(current.eventsInGroup));
  }

  function switchKind(kind: SwapKind): void {
    resetLookup();
    Object.assign(state, switchSwapKind({ ...state }, kind));
  }

  watchImmediate(data, seedFrom);
  watch(entryType, switchKind);
  useFeeRows(() => state.hasFee, () => state.fee, emptySubEvent);

  return {
    form,
    isEvm,
    isPlain,
    isSolana,
    locations,
    lookupCanRetry,
    lookupHint,
    lookupLoading,
    retryLookup,
    save,
  };
}
