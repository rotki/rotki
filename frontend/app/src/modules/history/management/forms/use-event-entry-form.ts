import type { ComputedRef, ModelRef, Ref } from 'vue';
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType, toSnakeCase } from '@rotki/common';
import { generateUUID } from '@shared/utils';
import { TRADE_LOCATION_EXTERNAL } from '@/modules/core/common/defaults';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { bitcoinAssetFor, chainEventRules, isChainEventKind } from '@/modules/history/management/forms/chain-event-entry-form';
import { EVENT_PRICE_INTENT_KEYS } from '@/modules/history/management/forms/eth-block-event-form';
import {
  emptyEventEntryForm,
  type EventEntryDefaults,
  type EventEntryFormState,
  type EventEntryKind,
  eventEntrySchema,
  relocateEventEntry,
} from '@/modules/history/management/forms/event-entry-form';
import {
  type EventEntryEvent,
  type EventEntryPayload,
  eventEntryStateFromEvent,
  eventEntryStateFromGroup,
  toEventEntryEditPayload,
  toEventEntryPayload,
} from '@/modules/history/management/forms/event-entry-payload';
import { useEvmTxAutoFill } from '@/modules/history/management/forms/use-evm-tx-lookup';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';

export type EventEntryFormData = StandaloneEventData<EventEntryEvent>;

interface UseEventEntryFormOptions {
  /** The dialog's data: a new event, one added into a transaction, or an event being edited. */
  readonly data: () => EventEntryFormData;
  /** The entry type picked in the dialog: a new bank transaction keeps it, any other new event takes its location's. */
  readonly entryType: () => EventEntryKind | undefined;
  /** The dialog's `prompt-on-close` flag, kept in step with the form being dirty. */
  readonly stateUpdated: ModelRef<boolean>;
}

interface UseEventEntryFormReturn {
  readonly form: ReturnType<typeof useHistoryEventForm<EventEntryFormState, EventEntryPayload, ReturnType<typeof toEventEntryEditPayload>>>['form'];
  readonly save: () => Promise<boolean>;
  readonly isPlain: ComputedRef<boolean>;
  readonly isEvm: ComputedRef<boolean>;
  readonly isBitcoin: ComputedRef<boolean>;
  /** Whether the kind has an address field: the EVM and Solana events. */
  readonly hasAddress: ComputedRef<boolean>;
  /** A bitcoin event's asset, which its chain decides. */
  readonly bitcoinAsset: ComputedRef<string>;
  readonly lookupLoading: Readonly<Ref<boolean>>;
  readonly lookupCanRetry: Readonly<Ref<boolean>>;
  readonly lookupHint: ComputedRef<string>;
  readonly retryLookup: () => Promise<void>;
}

/**
 * The event form's behaviour, for the plain, bank and chain event entry types.
 *
 * @remarks
 * The form seeds from the dialog's data. A new event takes the kind its location implies, so the
 * picker above offers one history event type: the kind switches in place, and counts as an edit.
 * A new bank transaction keeps that type, picked in the dialog. An event added into a transaction
 * takes that transaction's kind, and an edited event keeps the kind it was saved as. Only an EVM
 * event being added looks its transaction up as it is typed.
 */
export function useEventEntryForm({ data, entryType, stateUpdated }: UseEventEntryFormOptions): UseEventEntryFormReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { txChainsToLocation } = useSupportedChains();
  const { counterparties } = useHistoryEventCounterpartyMappings();

  const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

  /** Shared with the transaction lookup, which reports its failures as field errors too. */
  const errorMessages = ref<Record<string, string[]>>({});

  function defaults(): EventEntryDefaults {
    return { location: get(lastLocation) ?? TRADE_LOCATION_EXTERNAL, nextSequenceId: data().nextSequenceId };
  }

  /** Whether a new event's kind follows its location, which a new bank transaction's does not. */
  function followsLocation(): boolean {
    return data().type === 'add' && entryType() !== HistoryEventEntryType.BANK_TRANSACTION_EVENT;
  }

  function newEvent(): EventEntryFormState {
    const empty = emptyEventEntryForm(HistoryEventEntryType.HISTORY_EVENT, defaults());
    if (!followsLocation())
      return { ...empty, kind: HistoryEventEntryType.BANK_TRANSACTION_EVENT };
    return relocateEventEntry(empty, empty.location, get(txChainsToLocation));
  }

  const { form, save, seed } = useHistoryEventForm({
    errorMessages,
    initial: newEvent,
    priceIntentKeys: EVENT_PRICE_INTENT_KEYS,
    priceIntents: state => (state.priceIntent ? [state.priceIntent] : []),
    schema: computed(() => eventEntrySchema(data().type === 'edit', () => get(counterparties))),
    stateUpdated,
    toEditPayload: toEventEntryEditPayload,
    transform: state => toEventEntryPayload(state, generateUUID),
  });

  const { state } = form;

  const isPlain = computed<boolean>(() => !isChainEventKind(state.kind));
  const isEvm = computed<boolean>(() => state.kind === HistoryEventEntryType.EVM_EVENT);
  const isBitcoin = computed<boolean>(() => state.kind === HistoryEventEntryType.BITCOIN_EVENT);
  const hasAddress = computed<boolean>(() => isChainEventKind(state.kind) && !!chainEventRules(state.kind).address);
  const bitcoinAsset = computed<string>(() => bitcoinAssetFor(state.location));

  const {
    canRetry: lookupCanRetry,
    loading: lookupLoading,
    needsRelatedAddress,
    reset: resetLookup,
    retry: retryLookup,
  } = useEvmTxAutoFill({
    enabled: () => data().type === 'add' && get(isEvm),
    errorFields: { relatedAddress: 'locationLabel', txHash: 'txRef' },
    errorMessages,
    evmChain: () => toSnakeCase(state.location),
    onResolved: (result) => {
      state.timestamp = result.timestamp * 1000;
    },
    relatedAddress: () => state.locationLabel,
    txHash: () => state.txRef,
  });

  const lookupHint = computed<string>(() => {
    if (get(lookupLoading))
      return t('actions.evm_tx_lookup.loading');
    if (get(needsRelatedAddress))
      return t('actions.evm_tx_lookup.needs_related_address');
    return '';
  });

  function seedFrom(current: EventEntryFormData): void {
    resetLookup();
    if (current.type === 'edit')
      seed(eventEntryStateFromEvent(current.event, defaults()), [current.event.identifier]);
    else if (current.type === 'group-add')
      seed(eventEntryStateFromGroup(current.group, defaults()));
    else
      seed(newEvent());
  }

  /**
   * Gives an event being added the kind its location implies, and remembers the location for the
   * next new event.
   *
   * @remarks
   * It runs again when the EVM chains change, so a location picked before they loaded is re-read.
   */
  function relocate(location: string): void {
    if (location)
      set(lastLocation, location);
    if (!followsLocation())
      return;
    const relocated = relocateEventEntry({ ...state }, location, get(txChainsToLocation));
    if (relocated.kind !== state.kind)
      resetLookup();
    Object.assign(state, relocated);
  }

  /** Follows the picker between a history event and a bank transaction while a new event is open. */
  function followPicker(): void {
    if (data().type !== 'add')
      return;
    if (followsLocation())
      relocate(state.location);
    else
      state.kind = HistoryEventEntryType.BANK_TRANSACTION_EVENT;
  }

  watchImmediate(data, seedFrom);
  watch([(): string => state.location, txChainsToLocation], ([location]): void => relocate(location));
  watch(entryType, followPicker);

  return {
    bitcoinAsset,
    form,
    hasAddress,
    isBitcoin,
    isEvm,
    isPlain,
    lookupCanRetry,
    lookupHint,
    lookupLoading,
    retryLookup,
    save,
  };
}
