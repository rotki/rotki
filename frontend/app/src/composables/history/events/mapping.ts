import { type MaybeRef } from '@vueuse/core';
import {
  type HistoryEventProductData,
  type HistoryEventTypeData
} from '@/types/history/events/event-type';
import { type ActionDataEntry } from '@/types/action';

export const useHistoryEventMappings = createSharedComposable(() => {
  const { t, te } = useI18n();

  const {
    getTransactionTypeMappings,
    getHistoryEventCounterpartiesData,
    getHistoryEventProductsData
  } = useHistoryEventsApi();

  const defaultHistoryEventTypeData = () => ({
    globalMappings: {},
    eventCategoryDetails: {},
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

  const historyEventTypesData = useArrayMap(historyEventTypes, identifier => {
    const translationId = identifier.split('_').join(' ');
    const translationKey = `backend_mappings.events.history_event_type.${translationId}`;

    return {
      identifier,
      label: te(translationKey) ? t(translationKey) : toSentenceCase(identifier)
    };
  });

  const historyEventSubTypes: ComputedRef<string[]> = computed(() =>
    Object.values(get(historyEventTypeGlobalMapping))
      .flatMap(item => Object.keys(item))
      .filter(uniqueStrings)
  );

  const historyEventSubTypesData = useArrayMap(
    historyEventSubTypes,
    identifier => {
      const translationId = toSnakeCase(identifier);
      const translationKey = `backend_mappings.events.history_event_subtype.${translationId}`;
      return {
        identifier,
        label: te(translationKey)
          ? t(translationKey)
          : toSentenceCase(identifier)
      };
    }
  );

  const transactionEventTypesData = useRefMap(
    historyEventTypeData,
    ({ eventCategoryDetails }) =>
      Object.entries(eventCategoryDetails).map(([identifier, data]) => {
        const translationId = toSnakeCase(data.label);
        const translationKey = `backend_mappings.events.type.${translationId}`;

        return {
          ...data,
          identifier,
          label: te(translationKey)
            ? t(translationKey)
            : toSentenceCase(data.label)
        };
      })
  );

  const historyEventTypeGlobalMapping = useRefMap(
    historyEventTypeData,
    ({ globalMappings }) => globalMappings
  );

  const getEventType = (
    event: MaybeRef<{
      eventType?: string | null;
      eventSubtype?: string | null;
    }>
  ): ComputedRef<string | undefined> =>
    computed(() => {
      const { eventType, eventSubtype } = get(event);

      const eventTypeNormalized = eventType || 'none';
      const eventSubtypeNormalized = eventSubtype || 'none';

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

      const unknownLabel = t('backend_mappings.events.type.unknown');

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
    event: MaybeRef<{ counterparty: string | null; address?: string | null }>
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
      Object.entries(accountingEventsIcons).map(([identifier, icon]) => {
        const translationId = toSnakeCase(identifier);
        const translationKey = `backend_mappings.profit_loss_event_type.${translationId}`;

        return {
          identifier,
          icon,
          label: te(translationKey)
            ? t(translationKey)
            : toCapitalCase(identifier)
        };
      })
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

  const defaultHistoryEventProductsData = () => ({
    mappings: {},
    products: []
  });

  const historyEventProductsData: Ref<HistoryEventProductData> =
    asyncComputed<HistoryEventProductData>(
      () => getHistoryEventProductsData(),
      defaultHistoryEventProductsData(),
      {
        lazy: true
      }
    );

  const historyEventProductsMapping = useRefMap(
    historyEventProductsData,
    ({ mappings }) => mappings
  );

  const historyEventProducts = useRefMap(
    historyEventProductsData,
    ({ products }) => products
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
    historyEventCounterpartiesData,
    historyEventProductsData,
    counterparties,
    accountingEventsTypeData,
    getAccountingEventTypeData,
    historyEventProductsMapping,
    historyEventProducts
  };
});
