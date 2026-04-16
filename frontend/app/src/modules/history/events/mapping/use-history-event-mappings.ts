import type { MaybeRefOrGetter } from 'vue';
import type { ActionDataEntry } from '@/modules/core/common/action';
import type {
  HistoryEventCategoryDetailWithId,
  HistoryEventCategoryMapping,
  HistoryEventTypeData,
} from '@/modules/history/events/event-type';
import { HistoryEventEntryType, toCapitalCase, toSentenceCase, toSnakeCase } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { cloneDeep } from 'es-toolkit';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';

type Event = MaybeRefOrGetter<{
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
  const { notify } = useNotifications();

  const historyEventTypeGlobalMapping = computed(() => get(historyEventTypeData).globalMappings);

  const historyEventTypeByEntryTypeMapping = computed(() => get(historyEventTypeData).entryTypeMappings);

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

  const transactionEventTypesData = computed<HistoryEventCategoryMapping>(() => {
    const newEventCategoryDetails = cloneDeep(get(historyEventTypeData).eventCategoryDetails);
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

  const accountingEventsTypeData = computed<ActionDataEntry[]>(() =>
    Object.entries(get(historyEventTypeData).accountingEventsIcons).map(([identifier, icon]) => {
      const translationId = toSnakeCase(identifier);
      const translationKey = `backend_mappings.profit_loss_event_type.${translationId}`;

      return {
        icon,
        identifier,
        label: te(translationKey) ? t(translationKey) : toCapitalCase(identifier),
      };
    }));

  function findEventType(event: { entryType?: string; eventSubtype: string; eventType: string; isExit?: boolean; location?: string | null }): string | undefined {
    const { entryType, eventSubtype, eventType, isExit, location } = event;

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
  }

  const getEventType = (event: Event): ComputedRef<string | undefined> => computed<string | undefined>(() => findEventType(toValue(event)));

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

  function findEventTypeData(
    event: { counterparty?: string | null; entryType?: string; eventSubtype: string; eventType: string; isExit?: boolean; location?: string | null },
    showFallbackLabel = true,
  ): HistoryEventCategoryDetailWithId {
    const defaultKey = 'default';
    const type = findEventType(event);
    const { counterparty, eventSubtype, eventType } = event;
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
  }

  const getEventTypeData = (
    event: Event,
    showFallbackLabel = true,
  ): ComputedRef<HistoryEventCategoryDetailWithId> => computed(() =>
    findEventTypeData(toValue(event), showFallbackLabel),
  );

  const getAccountingEventTypeData = (type: MaybeRefOrGetter<string>): ComputedRef<ActionDataEntry> => computed(() => {
    const typeVal = toValue(type);
    return (
      get(accountingEventsTypeData).find(({ identifier }) => identifier === typeVal) || {
        icon: 'lu-circle-question-mark',
        identifier: typeVal,
        label: toCapitalCase(typeVal),
      }
    );
  });

  function getHistoryEventTypeName(eventType: string): string {
    return get(historyEventTypesData).find(item => item.identifier === eventType)?.label ?? toSentenceCase(eventType);
  }

  function getHistoryEventSubTypeName(eventSubtype: string): string {
    return get(historyEventSubTypesData).find(item => item.identifier === eventSubtype)?.label ?? toSentenceCase(eventSubtype);
  }

  const fetchMappings = async (): Promise<void> => {
    try {
      set(historyEventTypeData, await getTransactionTypeMappings());
    }
    catch (error: unknown) {
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
          message: getErrorMessage(error),
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
    findEventTypeData,
    getAccountingEventTypeData,
    getEventType,
    getEventTypeData,
    getHistoryEventSubTypeName,
    getHistoryEventTypeName,
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
