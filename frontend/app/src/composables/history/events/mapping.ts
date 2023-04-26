import { type MaybeRef } from '@vueuse/core';
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
  const { connected } = toRefs(useMainStore());

  const defaultHistoryEventTypeData = () => ({
    globalMappings: {},
    perProtocolMappings: {},
    eventCategoryDetails: {}
  });

  const historyEventTypeData: Ref<HistoryEventTypeData> =
    asyncComputed<HistoryEventTypeData>(
      () => {
        if (get(connected)) {
          return getTransactionTypeMappings();
        }
        return defaultHistoryEventTypeData();
      },
      defaultHistoryEventTypeData(),
      {
        lazy: true
      }
    );

  const historyEventCounterpartiesData: Ref<ActionDataEntry[]> = asyncComputed<
    ActionDataEntry[]
  >(
    () => {
      if (get(connected)) {
        return getHistoryEventCounterpartiesData();
      }
      return [];
    },
    [],
    {
      lazy: true
    }
  );

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
          `backend_mappings.events.history_event_subtype.${identifier.replace(
            / /g,
            '_'
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
            `backend_mappings.events.type.${data.label.replace(/ /g, '_')}`
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

  const getEventType = (
    event: MaybeRef<{
      eventType?: string | null;
      eventSubtype?: string | null;
      counterparty?: string | null;
      location?: string | null;
    }>
  ): ComputedRef<string | undefined> =>
    computed(() => {
      const { eventType, eventSubtype, counterparty, location } = get(event);

      const eventTypeNormalized = eventType || 'none';
      const eventSubtypeNormalized = eventSubtype || 'none';

      if (location && counterparty) {
        const subTypesFromPerProtocolMapping = get(
          historyEventTypePerProtocolMapping
        )[location]?.[counterparty]?.[eventTypeNormalized]?.[
          eventSubtypeNormalized
        ];

        if (subTypesFromPerProtocolMapping) {
          return subTypesFromPerProtocolMapping;
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
    counterparties
  };
});
