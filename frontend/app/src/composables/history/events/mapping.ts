import { type MaybeRef } from '@vueuse/core';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type HistoryEventTypeData } from '@/types/history/events/event-type';
import { type ActionDataEntry } from '@/types/action';
import {
  type EthDepositEvent,
  type EvmHistoryEvent
} from '@/types/history/events';

export const useHistoryEventMappings = createSharedComposable(() => {
  const { getTransactionTypeMappings, getHistoryEventCounterpartiesData } =
    useHistoryEventsApi();

  const { tc } = useI18n();

  const defaultHistoryEventTypeData = () => ({
    globalMappings: {},
    perProtocolMappings: {},
    eventCategoryDetails: {},
    exchangeMappings: {},
    accountingEventsIcons: {}
  });

  const historyEventTypeData: Ref<HistoryEventTypeData> =
    asyncComputed<HistoryEventTypeData>(
      () => getTransactionTypeMappings(),
      defaultHistoryEventTypeData(),
      {
        lazy: true
      }
    );

  const historyEventCounterpartiesData: Ref<ActionDataEntry[]> = asyncComputed<
    ActionDataEntry[]
  >(() => getHistoryEventCounterpartiesData(), [], {
    lazy: true
  });

  const historyEventTypes: ComputedRef<string[]> = computed(() =>
    Object.keys(get(historyEventTypeGlobalMapping))
  );

  const historyEventTypesData = useArrayMap(historyEventTypes, identifier => ({
    identifier,
    label:
      tc(
        `backend_mappings.events.history_event_type.${identifier
          .split('_')
          .join(' ')}`
      )?.toString() || toSentenceCase(identifier)
  }));

  const historyEventSubTypes: ComputedRef<string[]> = computed(() =>
    Object.values(get(historyEventTypeGlobalMapping)).flatMap(item =>
      Object.keys(item)
    )
  );

  const historyEventSubTypesData = useArrayMap(
    historyEventSubTypes,
    identifier => ({
      identifier,
      label:
        tc(
          `backend_mappings.events.history_event_subtype.${toSnakeCase(
            identifier
          )}`
        )?.toString() || toSentenceCase(identifier)
    })
  );

  const transactionEventTypesData = useRefMap(
    historyEventTypeData,
    ({ eventCategoryDetails }) =>
      Object.entries(eventCategoryDetails).map(([identifier, data]) => ({
        ...data,
        identifier,
        label:
          tc(
            `backend_mappings.events.type.${toSnakeCase(data.label)}`
          )?.toString() || toSentenceCase(data.label)
      }))
  );

  const historyEventTypeGlobalMapping = useRefMap(
    historyEventTypeData,
    ({ globalMappings }) => globalMappings
  );

  const historyEventTypePerProtocolMapping = useRefMap(
    historyEventTypeData,
    ({ perProtocolMappings }) => perProtocolMappings
  );

  const historyEventTypeExchangeMapping = useRefMap(
    historyEventTypeData,
    ({ exchangeMappings }) => exchangeMappings
  );

  const getEventType = (
    event: MaybeRef<{
      eventType?: string | null;
      eventSubtype?: string | null;
      counterparty?: string | null;
      location?: string | null;
      entryType: HistoryEventEntryType;
    }>
  ): ComputedRef<string | undefined> =>
    computed(() => {
      const { eventType, eventSubtype, counterparty, location, entryType } =
        get(event);

      const eventTypeNormalized = eventType || 'none';
      const eventSubtypeNormalized = eventSubtype || 'none';

      if (
        entryType === HistoryEventEntryType.EVM_EVENT &&
        location &&
        counterparty
      ) {
        const subTypesFromPerProtocolMapping = get(
          historyEventTypePerProtocolMapping
        )[location]?.[counterparty]?.[eventTypeNormalized]?.[
          eventSubtypeNormalized
        ];

        if (subTypesFromPerProtocolMapping) {
          return subTypesFromPerProtocolMapping;
        }
      }

      if (entryType === HistoryEventEntryType.HISTORY_EVENT && location) {
        const subTypesFromExchangesMapping = get(
          historyEventTypeExchangeMapping
        )[location]?.[eventTypeNormalized]?.[eventSubtypeNormalized];

        if (subTypesFromExchangesMapping) {
          return subTypesFromExchangesMapping;
        }
      }

      return (
        get(historyEventTypeGlobalMapping)[eventTypeNormalized]?.[
          eventSubtypeNormalized
        ] ?? undefined
      );
    });

  const getEventTypeData = (
    event: MaybeRef<{
      eventType?: string | null;
      eventSubtype?: string | null;
      counterparty?: string | null;
      location?: string | null;
      entryType: HistoryEventEntryType;
    }>,
    showFallbackLabel = true
  ): ComputedRef<ActionDataEntry> =>
    computed(() => {
      const type = get(getEventType(event));

      if (type) {
        return get(transactionEventTypesData).find(
          ({ identifier }: ActionDataEntry) =>
            identifier.toLowerCase() === type.toLowerCase()
        )!;
      }

      const unknownLabel = tc('backend_mappings.events.type.unknown');

      const { eventType, eventSubtype } = get(event);
      const label = showFallbackLabel
        ? eventSubtype || eventType || unknownLabel
        : unknownLabel;

      return {
        identifier: '',
        label,
        icon: 'mdi-help',
        color: 'red'
      };
    });

  const { scrambleData, scrambleHex } = useScramble();

  const getEventCounterpartyData = (
    event: MaybeRef<EvmHistoryEvent | EthDepositEvent>
  ): ComputedRef<ActionDataEntry | null> =>
    computed(() => {
      const { counterparty, address } = get(event);
      const excludedCounterparty = ['gas'];

      if (counterparty && excludedCounterparty.includes(counterparty)) {
        return null;
      }

      if (counterparty && !isValidEthAddress(counterparty)) {
        const data = get(historyEventCounterpartiesData).find(
          ({ matcher, identifier }: ActionDataEntry) => {
            if (matcher) {
              return matcher(counterparty);
            }
            return identifier.toLowerCase() === counterparty.toLowerCase();
          }
        );

        if (data) {
          return {
            ...data,
            label: counterparty.toUpperCase()
          };
        }

        return {
          identifier: '',
          label: counterparty,
          icon: 'mdi-help',
          color: 'red'
        };
      }

      const usedLabel = counterparty || address;

      if (!usedLabel) {
        return null;
      }

      const counterpartyAddress = get(scrambleData)
        ? scrambleHex(usedLabel)
        : usedLabel;

      return {
        identifier: '',
        label: counterpartyAddress || ''
      };
    });

  const counterparties = useArrayMap(
    historyEventCounterpartiesData,
    ({ identifier }) => identifier
  );

  const accountingEventsTypeData: Ref<ActionDataEntry[]> = useRefMap(
    historyEventTypeData,
    ({ accountingEventsIcons }) =>
      Object.entries(accountingEventsIcons).map(([identifier, icon]) => ({
        identifier,
        icon,
        label:
          tc(
            `backend_mappings.profit_loss_event_type.${toSnakeCase(identifier)}`
          )?.toString() || toCapitalCase(identifier)
      }))
  );

  const getAccountingEventTypeData = (
    type: MaybeRef<string>
  ): ComputedRef<ActionDataEntry> => {
    const typeVal = get(type);
    return computed(
      () =>
        get(accountingEventsTypeData).find(
          ({ identifier }) => identifier === typeVal
        ) || {
          identifier: typeVal,
          icon: 'mdi-help',
          label: toCapitalCase(typeVal)
        }
    );
  };

  return {
    historyEventTypeData,
    historyEventTypes,
    historyEventTypesData,
    historyEventSubTypes,
    historyEventSubTypesData,
    transactionEventTypesData,
    getEventType,
    getEventTypeData,
    getEventCounterpartyData,
    historyEventTypeGlobalMapping,
    historyEventTypePerProtocolMapping,
    historyEventCounterpartiesData,
    counterparties,
    accountingEventsTypeData,
    getAccountingEventTypeData
  };
});
