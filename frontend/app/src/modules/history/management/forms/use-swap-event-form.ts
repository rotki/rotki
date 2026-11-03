import type { ComputedRef, ModelRef, Ref } from 'vue';
import type { EvmHistoryEvent, EvmSwapEvent, SolanaEvent, SolanaSwapEvent, SwapEvent } from '@/modules/history/events/schemas';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType, toSnakeCase } from '@rotki/common';
import { generateUUID } from '@shared/utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { collectPriceIntents } from '@/modules/history/management/forms/price-intent';
import { type AddPayload, emptySwapForm, isCompleteSwapGroup, relocateSwap, type SwapFormState, swapIdentifiers, swapSchema, swapServerErrorPaths, swapStateForGroupAdd, swapStateFromEvents, toSwapEditPayload, toSwapPayload } from '@/modules/history/management/forms/swap-event-form';
import { emptySubEvent, SUB_EVENT_PRICE_INTENT_KEYS } from '@/modules/history/management/forms/swap/swap-sub-event';
import { useFeeRows } from '@/modules/history/management/forms/swap/use-fee-rows';
import { useEvmTxAutoFill } from '@/modules/history/management/forms/use-evm-tx-lookup';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';

/** The fields a move of location may empty, when they are not valid on the new chain. */
const CARRIED_FIELDS = ['address', 'txRef'] as const;

export type SwapFormData = StandaloneEventData<EvmHistoryEvent | SolanaEvent> | GroupEventData<SwapEvent | EvmSwapEvent | SolanaSwapEvent>;

interface UseSwapEventFormOptions {
  /** The dialog's data: a new swap, one added into a transaction, or a group being edited. */
  readonly data: () => SwapFormData;
  /** The dialog's `prompt-on-close` flag, kept in step with the form being dirty. */
  readonly stateUpdated: ModelRef<boolean>;
}

interface UseSwapEventFormReturn {
  readonly form: ReturnType<typeof useHistoryEventForm<SwapFormState, AddPayload, ReturnType<typeof toSwapEditPayload>>>['form'];
  readonly save: () => Promise<boolean>;
  readonly isEvm: ComputedRef<boolean>;
  readonly isPlain: ComputedRef<boolean>;
  /** Whether the group being edited is half a swap, which the form shows an error for instead of fields. */
  readonly incomplete: Readonly<Ref<boolean>>;
  readonly lookupLoading: Readonly<Ref<boolean>>;
  readonly lookupCanRetry: Readonly<Ref<boolean>>;
  readonly lookupHint: ComputedRef<string>;
  readonly retryLookup: () => Promise<void>;
}

/**
 * The swap form's behaviour, for the three swap entry types.
 *
 * @remarks
 * The form seeds from the dialog's data. A swap being added starts as a plain swap and takes the kind
 * its location implies, so the picker above offers one swap type: the kind switches in place, and
 * counts as an edit. A swap added into a transaction takes that transaction's chain, and an edited
 * swap keeps the kind it was saved as.
 * Only an EVM swap being added looks its transaction up as it is typed.
 */
export function useSwapEventForm({ data, stateUpdated }: UseSwapEventFormOptions): UseSwapEventFormReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { txChainsToLocation } = useSupportedChains();

  /** Shared with the transaction lookup, which reports its failures as field errors too. */
  const errorMessages = ref<Record<string, string[]>>({});

  const incomplete = shallowRef<boolean>(false);

  const { form, save: saveForm, seed } = useHistoryEventForm({
    errorMessages,
    initial: emptySwapForm,
    priceIntentKeys: SUB_EVENT_PRICE_INTENT_KEYS,
    priceIntents: state => collectPriceIntents(state.spend, state.receive, state.fee),
    schema: swapSchema(),
    serverErrorPaths: (errors, { kind }) => swapServerErrorPaths(kind, errors),
    stateUpdated,
    toEditPayload: toSwapEditPayload,
    transform: state => toSwapPayload(state, generateUUID),
  });

  const { state } = form;

  const isEvm = computed<boolean>(() => state.kind === HistoryEventEntryType.EVM_SWAP_EVENT);
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

  const lookupHint = computed<string>(() => {
    if (get(lookupLoading))
      return t('actions.evm_tx_lookup.loading');
    if (get(needsRelatedAddress))
      return t('actions.evm_tx_lookup.needs_related_address_swap');
    return '';
  });

  function seedFrom(current: SwapFormData): void {
    resetLookup();
    set(incomplete, current.type === 'edit-group' && !isCompleteSwapGroup(current.eventsInGroup));
    if (get(incomplete))
      return;
    if (current.type === 'group-add')
      seed(swapStateForGroupAdd(current.group, current.nextSequenceId.toString()));
    else if (current.type === 'edit-group')
      seed(swapStateFromEvents(current.eventsInGroup), swapIdentifiers(current.eventsInGroup));
  }

  /** Saves the swap, unless it is half a swap, which has nothing complete to save. */
  async function save(): Promise<boolean> {
    if (get(incomplete))
      return false;
    return saveForm();
  }

  /**
   * Gives a swap being added the kind its location implies.
   *
   * @remarks
   * It runs again when the EVM chains change, so a location picked before they loaded is re-read.
   * A reference or address the move emptied counts as untouched again, so it is not flagged as
   * missing before the user has had a chance to fill it in.
   */
  function relocate(location: string): void {
    if (data().type !== 'add')
      return;
    const relocated = relocateSwap({ ...state }, location, get(txChainsToLocation));
    if (relocated.kind !== state.kind)
      resetLookup();
    const emptied = CARRIED_FIELDS.filter(path => state[path] && !relocated[path]);
    Object.assign(state, relocated);
    emptied.forEach(path => form.untouch(path));
  }

  watchImmediate(data, seedFrom);
  watch([(): string => state.location, txChainsToLocation], ([location]): void => relocate(location));
  useFeeRows(() => state.hasFee, () => state.fee, emptySubEvent);

  return {
    form,
    incomplete: readonly(incomplete),
    isEvm,
    isPlain,
    lookupCanRetry,
    lookupHint,
    lookupLoading,
    retryLookup,
    save,
  };
}
