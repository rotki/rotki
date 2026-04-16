import type { MaybeRef } from 'vue';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type {
  MatchedKeywordWithBehaviour,
  SearchMatcher,
} from '@/modules/table/filtering';
import {
  HistoryEventEntryType,
  isValidAddress,
  isValidTxHashOrSignature,
} from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { z } from 'zod/v4';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { arrayify } from '@/modules/common/data/array';
import { uniqueStrings } from '@/modules/common/data/data';
import { dateDeserializer, dateRangeValidator, dateSerializer, getDateInputISOFormat } from '@/modules/common/data/date';
import { assetSuggestions } from '@/modules/common/display/assets';
import {
  isEthBlockEventType,
  isEthDepositEventType,
  isEvmEventType,
  isOnlineHistoryEventType,
  isSolanaEventType,
  isWithdrawalEventType,
} from '@/modules/history/event-utils';
import { useHistoryStore } from '@/store/history';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

enum HistoryEventFilterKeys {
  START = 'start',
  END = 'end',
  ASSET = 'asset',
  PROTOCOL = 'protocol',
  EVENT_TYPE = 'event_type',
  EVENT_SUBTYPE = 'event_subtype',
  LOCATION = 'location',
  ENTRY_TYPE = 'type',
  TX_HASHES = 'tx_hash',
  VALIDATOR_INDICES = 'validator_index',
  ADDRESSES = 'address',
  NOTES = 'notes',
}

enum HistoryEventFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
  ASSET = 'asset',
  PROTOCOL = 'counterparties',
  EVENT_TYPE = 'eventTypes',
  EVENT_SUBTYPE = 'eventSubtypes',
  LOCATION = 'location',
  ENTRY_TYPE = 'entryTypes',
  TX_HASHES = 'txRefs',
  VALIDATOR_INDICES = 'validatorIndices',
  ADDRESSES = 'addresses',
  NOTES = 'notesSubstring',
}

export type Matcher = SearchMatcher<HistoryEventFilterKeys, HistoryEventFilterValueKeys>;

export type Filters = MatchedKeywordWithBehaviour<HistoryEventFilterValueKeys>;

export function useHistoryEventFilter(
  disabled: {
    protocols?: boolean;
    locations?: boolean;
    period?: boolean;
    validators?: boolean;
    eventTypes?: boolean;
    eventSubtypes?: boolean;
  },
  entryTypes?: MaybeRef<HistoryEventEntryType[] | undefined>,
): FilterSchema<Filters, Matcher> {
  const filters = ref<Filters>({});

  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { historyEventTypeGlobalMapping, historyEventTypes } = useHistoryEventMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { assetSearch, getAssetInfo } = useAssetInfoRetrieval();
  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { t } = useI18n({ useScope: 'global' });

  const validSubtypeKeys = computed<string[]>(() => {
    if (disabled.eventSubtypes)
      return [];

    const globalMapping = get(historyEventTypeGlobalMapping);
    if (Object.keys(globalMapping).length === 0)
      return [];

    let selectedEventTypes = get(filters)?.eventTypes || [];
    if (!Array.isArray(selectedEventTypes))
      selectedEventTypes = [selectedEventTypes.toString()];

    const keys: string[] = [];
    if (selectedEventTypes.length > 0) {
      selectedEventTypes.forEach((selectedEventType) => {
        const globalMappingFound = globalMapping[selectedEventType];
        if (globalMappingFound)
          keys.push(...Object.keys(globalMappingFound));
      });
    }
    else {
      for (const key in globalMapping)
        keys.push(...Object.keys(globalMapping[key]));
    }

    return keys;
  });

  watch(validSubtypeKeys, (keys) => {
    if (keys.length === 0)
      return;

    let selectedEventSubtypes = get(filters)?.eventSubtypes || [];
    if (!Array.isArray(selectedEventSubtypes))
      selectedEventSubtypes = [selectedEventSubtypes.toString()];

    if (selectedEventSubtypes.length === 0)
      return;

    const filteredEventSubtypes = selectedEventSubtypes.filter(item => keys.includes(item));

    if (!isEqual(filteredEventSubtypes, selectedEventSubtypes)) {
      set(filters, {
        ...get(filters),
        eventSubtypes: filteredEventSubtypes.length > 0 ? filteredEventSubtypes : undefined,
      });
    }
  });

  const matchers = computed<Matcher[]>(() => {
    const selectedLocation = get(filters)?.location;
    const locationString = (Array.isArray(selectedLocation) ? selectedLocation[0] : selectedLocation)?.toString();

    const data: Matcher[] = [
      ...(disabled?.period
        ? []
        : ([
            {
              description: t('transactions.filter.start_date'),
              deserializer: dateDeserializer(dateInputFormat),
              hint: t('transactions.filter.date_hint', {
                format: getDateInputISOFormat(get(dateInputFormat)),
              }),
              key: HistoryEventFilterKeys.START,
              keyValue: HistoryEventFilterValueKeys.START,
              serializer: dateSerializer(dateInputFormat),
              string: true,
              suggestions: () => [],
              validate: dateRangeValidator(dateInputFormat, () => get(filters)?.toTimestamp?.toString(), 'start'),
            },
            {
              description: t('transactions.filter.end_date'),
              deserializer: dateDeserializer(dateInputFormat),
              hint: t('transactions.filter.date_hint', {
                format: getDateInputISOFormat(get(dateInputFormat)),
              }),
              key: HistoryEventFilterKeys.END,
              keyValue: HistoryEventFilterValueKeys.END,
              serializer: dateSerializer(dateInputFormat),
              string: true,
              suggestions: () => [],
              validate: dateRangeValidator(dateInputFormat, () => get(filters)?.fromTimestamp?.toString(), 'end'),
            },
          ] satisfies Matcher[])),
      {
        asset: true,
        description: t('transactions.filter.asset'),
        deserializer: getAssetInfo,
        key: HistoryEventFilterKeys.ASSET,
        keyValue: HistoryEventFilterValueKeys.ASSET,
        suggestions: assetSuggestions(assetSearch, locationString),
      },
      {
        description: t('transactions.filter.notes'),
        key: HistoryEventFilterKeys.NOTES,
        keyValue: HistoryEventFilterValueKeys.NOTES,
        string: true,
        suggestions: () => [],
        validate: (notes: string) => !!notes,
      },
    ];

    const entryTypesVal = get(entryTypes);
    const transactionEventsIncluded
      = !entryTypesVal || entryTypesVal.some(type => isEvmEventType(type) || isEthDepositEventType(type) || isSolanaEventType(type));

    const evmOrOnlineEventsIncluded
      = !entryTypesVal || entryTypesVal.some(type => isEvmEventType(type) || isOnlineHistoryEventType(type));

    const eventsWithValidatorIndexIncluded
      = !entryTypesVal
        || entryTypesVal.some(
          type => isWithdrawalEventType(type) || isEthBlockEventType(type) || isEthDepositEventType(type),
        );

    if (!disabled?.protocols && transactionEventsIncluded) {
      const counterpartiesVal = get(counterparties);
      data.push({
        description: t('transactions.filter.protocol'),
        key: HistoryEventFilterKeys.PROTOCOL,
        keyValue: HistoryEventFilterValueKeys.PROTOCOL,
        multiple: true,
        string: true,
        suggestions: () => counterpartiesVal,
        validate: (protocol: string) => !!protocol,
      });
    }

    if (!disabled?.locations) {
      data.push({
        description: t('transactions.filter.location'),
        key: HistoryEventFilterKeys.LOCATION,
        keyValue: HistoryEventFilterValueKeys.LOCATION,
        string: true,
        suggestions: () => get(associatedLocations),
        validate: location => !!location,
      });
    }

    if (!entryTypesVal || entryTypesVal.length > 1) {
      data.push({
        allowExclusion: true,
        behaviourRequired: true,
        description: t('transactions.filter.entry_type'),
        key: HistoryEventFilterKeys.ENTRY_TYPE,
        keyValue: HistoryEventFilterValueKeys.ENTRY_TYPE,
        multiple: true,
        string: true,
        suggestions: () => entryTypesVal ?? Object.values(HistoryEventEntryType),
        validate: (type: string) => !!type,
      });
    }

    if (evmOrOnlineEventsIncluded) {
      if (!disabled.eventTypes) {
        data.push({
          description: t('transactions.filter.event_type'),
          key: HistoryEventFilterKeys.EVENT_TYPE,
          keyValue: HistoryEventFilterValueKeys.EVENT_TYPE,
          multiple: true,
          string: true,
          suggestions: () => get(historyEventTypes),
          suggestionsToShow: -1,
          validate: (type: string) => !!type,
        });
      }

      if (!disabled.eventSubtypes) {
        const subtypeKeys = get(validSubtypeKeys);
        data.push({
          description: t('transactions.filter.event_subtype'),
          key: HistoryEventFilterKeys.EVENT_SUBTYPE,
          keyValue: HistoryEventFilterValueKeys.EVENT_SUBTYPE,
          multiple: true,
          string: true,
          suggestions: () => subtypeKeys.filter(uniqueStrings),
          suggestionsToShow: -1,
          validate: (type: string) => subtypeKeys.includes(type),
        });
      }
    }

    if (transactionEventsIncluded) {
      data.push(
        {
          description: t('transactions.filter.tx_hash'),
          key: HistoryEventFilterKeys.TX_HASHES,
          keyValue: HistoryEventFilterValueKeys.TX_HASHES,
          multiple: true,
          string: true,
          suggestions: () => [],
          validate: (txHash: string) => isValidTxHashOrSignature(txHash),
        },
        {
          description: t('transactions.filter.address'),
          key: HistoryEventFilterKeys.ADDRESSES,
          keyValue: HistoryEventFilterValueKeys.ADDRESSES,
          multiple: true,
          string: true,
          suggestions: () => [],
          validate: (address: string) => isValidAddress(address),
        },
      );
    }

    if (eventsWithValidatorIndexIncluded && !disabled?.validators) {
      data.push({
        description: t('transactions.filter.validator_index'),
        key: HistoryEventFilterKeys.VALIDATOR_INDICES,
        keyValue: HistoryEventFilterValueKeys.VALIDATOR_INDICES,
        multiple: true,
        string: true,
        suggestions: () => [],
        validate: (validatorIndex: string) => !!validatorIndex,
      });
    }

    return data;
  });

  const OptionalString = z.string().optional();
  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(arrayify)
    .optional();

  const RouteFilterSchema = z.object({
    [HistoryEventFilterValueKeys.START]: OptionalString,
    [HistoryEventFilterValueKeys.END]: OptionalString,
    [HistoryEventFilterValueKeys.ADDRESSES]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.ASSET]: OptionalString,
    [HistoryEventFilterValueKeys.ENTRY_TYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.EVENT_SUBTYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.EVENT_TYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.LOCATION]: OptionalString,
    [HistoryEventFilterValueKeys.NOTES]: OptionalString,
    [HistoryEventFilterValueKeys.PROTOCOL]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.TX_HASHES]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.VALIDATOR_INDICES]: OptionalMultipleString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
