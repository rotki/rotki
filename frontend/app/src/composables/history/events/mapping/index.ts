import type { MaybeRef } from '@vueuse/core';
import type { ActionDataEntry } from '@/types/action';
import type {
  HistoryEventCategoryDetailWithId,
  HistoryEventCategoryMapping,
  HistoryEventTypeData,
} from '@/types/history/events/event-type';
import { HistoryEventEntryType, toCapitalCase, toSentenceCase, toSnakeCase } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { cloneDeep } from 'es-toolkit';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useLocationStore } from '@/store/locations';
import { useNotificationsStore } from '@/store/notifications';
import { uniqueStrings } from '@/utils/data';

type Event = MaybeRef<{
  eventType: string;
  eventSubtype: string;
  counterparty?: string | null;
  location?: string | null;
  entryType?: string;
  isExit?: boolean;
}>;

export const useHistoryEventMappings = createSharedComposable(() => {
  // eslint-disable-next-line @typescript-eslint/unbound-method
  const { t, te } = useI18n({ useScope: 'global' });

  const historyEventTypeData = ref<HistoryEventTypeData>(({
    accountingEventsIcons: {},
    entryTypeMappings: {},
    eventCategoryDetails: {},
    globalMappings: {},
  }));

  const { allExchanges } = storeToRefs(useLocationStore());

  const { getTransactionTypeMappings } = useHistoryEventsApi();
  const { notify } = useNotificationsStore();

  const historyEventTypeGlobalMapping = useRefMap(historyEventTypeData, ({ globalMappings }) => globalMappings);

  const historyEventTypeByEntryTypeMapping = useRefMap(
    historyEventTypeData,
    ({ entryTypeMappings }) => entryTypeMappings,
  );

  const historyEventTypes = computed<string[]>(() => Object.keys(get(historyEventTypeGlobalMapping)));

  const historyEventTypesData = useArrayMap(historyEventTypes, (identifier) => {
    const translationId = identifier.split('_').join(' ');
    const translationKey = `backend_mappings.events.history_event_type.${translationId}`;

    return {
      identifier,
      label: te(translationKey) ? t(translationKey) : toSentenceCase(identifier),
    };
  });

  const historyEventSubTypes = computed<string[]>(() =>
    Object.values(get(historyEventTypeGlobalMapping))
      .flatMap(item => Object.keys(item))
      .filter(uniqueStrings),
  );

  const historyEventSubTypesData = useArrayMap(historyEventSubTypes, (identifier) => {
    const translationId = toSnakeCase(identifier);
    const translationKey = `backend_mappings.events.history_event_subtype.${translationId}`;
    return {
      identifier,
      label: te(translationKey) ? t(translationKey) : toSentenceCase(identifier),
    };
  });

  const transactionEventTypesData: ComputedRef<HistoryEventCategoryMapping> = useRefMap(historyEventTypeData, ({ eventCategoryDetails }) => {
    const newEventCategoryDetails = cloneDeep(eventCategoryDetails);
    for (const eventCategory in newEventCategoryDetails) {
      const counterpartyMappings = newEventCategoryDetails[eventCategory].counterpartyMappings;
      for (const counterparty in counterpartyMappings) {
        const label = counterpartyMappings[counterparty].label;
        const translationId = toSnakeCase(label);
        const translationKey = `backend_mappings.events.type.${translationId}`;
        counterpartyMappings[counterparty].label = te(translationKey) ? t(translationKey) : toSentenceCase(label);
      }
    }
    return newEventCategoryDetails;
  });

  const accountingEventsTypeData: Ref<ActionDataEntry[]> = useRefMap(historyEventTypeData, ({ accountingEventsIcons }) =>
    Object.entries(accountingEventsIcons).map(([identifier, icon]) => {
      const translationId = toSnakeCase(identifier);
      const translationKey = `backend_mappings.profit_loss_event_type.${translationId}`;

      return {
        icon,
        identifier,
        label: te(translationKey) ? t(translationKey) : toCapitalCase(identifier),
      };
    }));

  const getEventType = (event: Event): ComputedRef<string | undefined> => computed(() => {
    const { entryType, eventSubtype, eventType, isExit, location } = get(event);

    if (entryType === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT) {
      const withdrawalEntryType = get(historyEventTypeByEntryTypeMapping)[entryType]
        ?.[eventType]
        ?.[eventSubtype]
        ?.[isExit ? 'isExit' : 'notExit'];

      if (withdrawalEntryType)
        return withdrawalEntryType;
    }

    const isExchange = !!location && get(allExchanges).includes(location);

    const mapping = get(historyEventTypeGlobalMapping)[eventType]
      ?.[eventSubtype];

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
    const label = showFallbackLabel ? eventSubtype || eventType || unknownLabel : unknownLabel;

    return {
      color: 'error',
      direction: 'neutral',
      icon: 'lu-circle-question-mark',
      identifier: '',
      label,
    };
  }

  const getEventTypeData = (
    event: Event,
    showFallbackLabel = true,
  ): ComputedRef<HistoryEventCategoryDetailWithId> => computed(() => {
    const defaultKey = 'default';
    const type = get(getEventType(event));
    const { counterparty, eventSubtype, eventType } = get(event);
    const counterpartyVal = counterparty || defaultKey;
    const data = type && get(transactionEventTypesData)[type];

    if (type && data) {
      const categoryDetail = data.counterpartyMappings[counterpartyVal] || data.counterpartyMappings[defaultKey];

      if (categoryDetail) {
        return {
          ...categoryDetail,
          direction: data.direction,
          identifier: counterpartyVal !== defaultKey ? counterpartyVal : type,
        };
      }
    }

    return getFallbackData(showFallbackLabel, eventSubtype, eventType);
  });

  const getAccountingEventTypeData = (type: MaybeRef<string>): ComputedRef<ActionDataEntry> => computed(() => {
    const typeVal = get(type);
    return (
      get(accountingEventsTypeData).find(({ identifier }) => identifier === typeVal) || {
        icon: 'lu-circle-question-mark',
        identifier: typeVal,
        label: toCapitalCase(typeVal),
      }
    );
  });

  const fetchMappings = async (): Promise<void> => {
    try {
      set(historyEventTypeData, await getTransactionTypeMappings());
    }
    catch (error: any) {
      notify({
        action: [
          {
            action: async (): Promise<void> => fetchMappings(),
            icon: 'lu-refresh-ccw',
            label: t('actions.history_events.fetch_mapping.actions.fetch_again'),
          },
        ],
        display: true,
        message: t('actions.history_events.fetch_mapping.error.description', {
          message: error.message,
        }),
        title: t('actions.history_events.fetch_mapping.error.title'),
      });
    }
  };

  onBeforeMount(() => {
    startPromise(fetchMappings());
  });

  return {
    accountingEventsTypeData,
    getAccountingEventTypeData,
    getEventType,
    getEventTypeData,
    historyEventSubTypes,
    historyEventSubTypesData,
    historyEventTypeData,
    historyEventTypeGlobalMapping,
    historyEventTypes,
    historyEventTypesData,
    refresh: fetchMappings,
    transactionEventTypesData,
  };
});
