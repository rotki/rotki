import { type MaybeRef } from '@vueuse/core';
import { cloneDeep } from 'lodash-es';
import {
  type HistoryEventCategoryDetailWithId,
  type HistoryEventCategoryMapping,
  type HistoryEventProductData,
  type HistoryEventTypeData
} from '@/types/history/events/event-type';
import { type ActionDataEntry } from '@/types/action';

type Event = MaybeRef<{
  eventType: string;
  eventSubtype: string;
  counterparty?: string | null;
}>;

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

  const transactionEventTypesData: ComputedRef<HistoryEventCategoryMapping> =
    useRefMap(historyEventTypeData, ({ eventCategoryDetails }) => {
      const newEventCategoryDetails = cloneDeep(eventCategoryDetails);
      for (const eventCategory in newEventCategoryDetails) {
        const counterpartyMappings =
          newEventCategoryDetails[eventCategory].counterpartyMappings;
        for (const counterparty in counterpartyMappings) {
          const label = counterpartyMappings[counterparty].label;
          const translationId = toSnakeCase(label);
          const translationKey = `backend_mappings.events.type.${translationId}`;
          counterpartyMappings[counterparty].label = te(translationKey)
            ? t(translationKey)
            : toSentenceCase(label);
        }
      }
      return newEventCategoryDetails;
    });

  const historyEventTypeGlobalMapping = useRefMap(
    historyEventTypeData,
    ({ globalMappings }) => globalMappings
  );

  const getEventType = (
    event: MaybeRef<{
      eventType: string;
      eventSubtype: string;
    }>
  ): ComputedRef<string | undefined> =>
    computed(() => {
      const { eventType, eventSubtype } = get(event);

      return get(historyEventTypeGlobalMapping)[eventType]?.[eventSubtype];
    });

  function getFallbackData(
    showFallbackLabel: boolean,
    eventSubtype: string,
    eventType: string
  ): HistoryEventCategoryDetailWithId {
    const unknownLabel = t('backend_mappings.events.type.unknown');
    const label = showFallbackLabel
      ? eventSubtype || eventType || unknownLabel
      : unknownLabel;

    return {
      identifier: '',
      label,
      icon: 'question-line',
      color: 'error',
      direction: 'neutral'
    };
  }

  const getEventTypeData = (
    event: Event,
    showFallbackLabel = true
  ): ComputedRef<HistoryEventCategoryDetailWithId> =>
    computed(() => {
      const defaultKey = 'default';
      const type = get(getEventType(event));
      const { counterparty, eventType, eventSubtype } = get(event);
      const counterpartyVal = counterparty || defaultKey;
      const data = type && get(transactionEventTypesData)[type];

      if (type && data) {
        const categoryDetail =
          data.counterpartyMappings[counterpartyVal] ||
          data.counterpartyMappings[defaultKey];

        if (categoryDetail) {
          return {
            ...categoryDetail,
            identifier: counterpartyVal !== defaultKey ? counterpartyVal : type,
            direction: data.direction
          };
        }
      }

      return getFallbackData(showFallbackLabel, eventSubtype, eventType);
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
          icon: 'question-line',
          color: 'error'
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
  ): ComputedRef<ActionDataEntry> =>
    computed(() => {
      const typeVal = get(type);
      return (
        get(accountingEventsTypeData).find(
          ({ identifier }) => identifier === typeVal
        ) || {
          identifier: typeVal,
          icon: 'question-line',
          label: toCapitalCase(typeVal)
        }
      );
    });

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
