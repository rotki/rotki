import { cloneDeep } from 'lodash-es';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import type { MaybeRef } from '@vueuse/core';
import type {
  HistoryEventCategoryDetailWithId,
  HistoryEventCategoryMapping,
  HistoryEventTypeData,
} from '@/types/history/events/event-type';
import type { ActionDataEntry } from '@/types/action';

type Event = MaybeRef<{
  eventType: string;
  eventSubtype: string;
  counterparty?: string | null;
  location?: string | null;
  entryType?: string;
  isExit?: boolean;
}>;

export const useHistoryEventMappings = createSharedComposable(() => {
  const { t, te } = useI18n();

  const { allExchanges } = storeToRefs(useLocationStore());

  const {
    getTransactionTypeMappings,
  } = useHistoryEventsApi();

  const defaultHistoryEventTypeData = () => ({
    globalMappings: {},
    eventCategoryDetails: {},
    accountingEventsIcons: {},
    entryTypeMappings: {},
  });

  const { notify } = useNotificationsStore();

  const fetchError = ref<boolean>(true);

  const refresh = async () => {
    if (get(fetchError)) {
      try {
        set(historyEventTypeData, await getTransactionTypeMappings());
      }
      catch (error: any) {
        onFetchError(error);
      }
    }
  };

  const onFetchError = (e: any) => {
    set(fetchError, true);
    notify({
      display: true,
      title: t('actions.history_events.fetch_mapping.error.title'),
      message: t('actions.history_events.fetch_mapping.error.description', {
        message: e.message,
      }),
      action: [
        {
          label: t('actions.history_events.fetch_mapping.actions.fetch_again'),
          action: refresh,
          icon: 'refresh-line',
        },
      ],
    });
  };

  const historyEventTypeData: Ref<HistoryEventTypeData> = asyncComputed<HistoryEventTypeData>(
    () => {
      set(fetchError, false);
      return getTransactionTypeMappings();
    },
    defaultHistoryEventTypeData(),
    {
      onError: onFetchError,
    },
  );

  const historyEventTypeGlobalMapping = useRefMap(
    historyEventTypeData,
    ({ globalMappings }) => globalMappings,
  );

  const historyEventTypeByEntryTypeMapping = useRefMap(
    historyEventTypeData,
    ({ entryTypeMappings }) => entryTypeMappings,
  );

  const historyEventTypes: ComputedRef<string[]> = computed(() =>
    Object.keys(get(historyEventTypeGlobalMapping)),
  );

  const historyEventTypesData = useArrayMap(historyEventTypes, (identifier) => {
    const translationId = identifier.split('_').join(' ');
    const translationKey = `backend_mappings.events.history_event_type.${translationId}`;

    return {
      identifier,
      label: te(translationKey) ? t(translationKey) : toSentenceCase(identifier),
    };
  });

  const historyEventSubTypes: ComputedRef<string[]> = computed(() =>
    Object.values(get(historyEventTypeGlobalMapping))
      .flatMap(item => Object.keys(item))
      .filter(uniqueStrings),
  );

  const historyEventSubTypesData = useArrayMap(
    historyEventSubTypes,
    (identifier) => {
      const translationId = toSnakeCase(identifier);
      const translationKey = `backend_mappings.events.history_event_subtype.${translationId}`;
      return {
        identifier,
        label: te(translationKey)
          ? t(translationKey)
          : toSentenceCase(identifier),
      };
    },
  );

  const transactionEventTypesData: ComputedRef<HistoryEventCategoryMapping> = useRefMap(historyEventTypeData, ({ eventCategoryDetails }) => {
    const newEventCategoryDetails = cloneDeep(eventCategoryDetails);
    for (const eventCategory in newEventCategoryDetails) {
      const counterpartyMappings
          = newEventCategoryDetails[eventCategory].counterpartyMappings;
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

  const getEventType = (event: Event): ComputedRef<string | undefined> => computed(() => {
    const { eventType, eventSubtype, entryType, isExit, location } = get(event);

    if (entryType === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT) {
      const withdrawalEntryType = get(historyEventTypeByEntryTypeMapping)[entryType]?.[
        eventType
      ]?.[eventSubtype]?.[isExit ? 'isExit' : 'notExit'];

      if (withdrawalEntryType)
        return withdrawalEntryType;
    }

    const isExchange = !!location && get(allExchanges).includes(location);

    const mapping = get(historyEventTypeGlobalMapping)[eventType]?.[eventSubtype];

    if (!mapping)
      return undefined;

    if (!isExchange)
      return mapping.default;

    return mapping.exchange || mapping.default;
  });

  function getFallbackData(
    showFallbackLabel: boolean,
    eventSubtype: string,
    eventType: string,
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
      direction: 'neutral',
    };
  }

  const getEventTypeData = (
    event: Event,
    showFallbackLabel = true,
  ): ComputedRef<HistoryEventCategoryDetailWithId> => computed(() => {
    const defaultKey = 'default';
    const type = get(getEventType(event));
    const { counterparty, eventType, eventSubtype } = get(event);
    const counterpartyVal = counterparty || defaultKey;
    const data = type && get(transactionEventTypesData)[type];

    if (type && data) {
      const categoryDetail
          = data.counterpartyMappings[counterpartyVal]
          || data.counterpartyMappings[defaultKey];

      if (categoryDetail) {
        return {
          ...categoryDetail,
          identifier: counterpartyVal !== defaultKey ? counterpartyVal : type,
          direction: data.direction,
        };
      }
    }

    return getFallbackData(showFallbackLabel, eventSubtype, eventType);
  });

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
            : toCapitalCase(identifier),
        };
      }),
  );

  const getAccountingEventTypeData = (
    type: MaybeRef<string>,
  ): ComputedRef<ActionDataEntry> => computed(() => {
    const typeVal = get(type);
    return (
      get(accountingEventsTypeData).find(
        ({ identifier }) => identifier === typeVal,
      ) || {
        identifier: typeVal,
        icon: 'question-line',
        label: toCapitalCase(typeVal),
      }
    );
  });

  return {
    historyEventTypeData,
    historyEventTypes,
    historyEventTypesData,
    historyEventSubTypes,
    historyEventSubTypesData,
    transactionEventTypesData,
    getEventType,
    getEventTypeData,
    historyEventTypeGlobalMapping,
    accountingEventsTypeData,
    getAccountingEventTypeData,
    refresh,
  };
});
