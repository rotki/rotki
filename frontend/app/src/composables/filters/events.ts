import { z } from 'zod';
import { HistoryEventEntryType } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { uniqueStrings } from '@/utils/data';
import { arrayify } from '@/utils/array';
import { isEthBlockEventType, isEthDepositEventType, isEvmEventType, isOnlineHistoryEventType, isWithdrawalEventType } from '@/utils/history/events';
import { getDateInputISOFormat } from '@/utils/date';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useHistoryStore } from '@/store/history';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useHistoryEventProductMappings } from '@/composables/history/events/mapping/product';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { assetDeserializer, assetSuggestions, dateDeserializer, dateSerializer, dateValidator } from '@/utils/assets';
import type {
  MatchedKeywordWithBehaviour,
  SearchMatcher,

} from '@/types/filtering';
import type { MaybeRef } from '@vueuse/core';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';

enum HistoryEventFilterKeys {
  START = 'start',
  END = 'end',
  ASSET = 'asset',
  PROTOCOL = 'protocol',
  EVENT_TYPE = 'event_type',
  EVENT_SUBTYPE = 'event_subtype',
  LOCATION = 'location',
  PRODUCT = 'product',
  ENTRY_TYPE = 'type',
  TX_HASHES = 'tx_hash',
  VALIDATOR_INDICES = 'validator_index',
  ADDRESSES = 'address',
}

enum HistoryEventFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
  ASSET = 'asset',
  PROTOCOL = 'counterparties',
  EVENT_TYPE = 'eventTypes',
  EVENT_SUBTYPE = 'eventSubtypes',
  LOCATION = 'location',
  PRODUCT = 'products',
  ENTRY_TYPE = 'entryTypes',
  TX_HASHES = 'txHashes',
  VALIDATOR_INDICES = 'validatorIndices',
  ADDRESSES = 'addresses',
}

export type Matcher = SearchMatcher<HistoryEventFilterKeys, HistoryEventFilterValueKeys>;

export type Filters = MatchedKeywordWithBehaviour<HistoryEventFilterValueKeys>;

export function useHistoryEventFilter(
  disabled: {
    protocols?: boolean;
    products?: boolean;
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
  const { historyEventProducts } = useHistoryEventProductMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { assetInfo, assetSearch } = useAssetInfoRetrieval();
  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { t } = useI18n();

  const matchers = computed<Matcher[]>(() => {
    let selectedLocation = get(filters)?.location;
    if (Array.isArray(selectedLocation))
      selectedLocation = selectedLocation[0] || undefined;
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
              validate: dateValidator(dateInputFormat),
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
              validate: dateValidator(dateInputFormat),
            },
          ] satisfies Matcher[])),
      {
        asset: true,
        description: t('transactions.filter.asset'),
        deserializer: assetDeserializer(assetInfo),
        key: HistoryEventFilterKeys.ASSET,
        keyValue: HistoryEventFilterValueKeys.ASSET,
        suggestions: assetSuggestions(assetSearch, selectedLocation?.toString()),
      },
    ];

    const entryTypesVal = get(entryTypes);
    const evmOrEthDepositEventsIncluded
      = !entryTypesVal || entryTypesVal.some(type => isEvmEventType(type) || isEthDepositEventType(type));

    const evmOrOnlineEventsIncluded
      = !entryTypesVal || entryTypesVal.some(type => isEvmEventType(type) || isOnlineHistoryEventType(type));

    const eventsWithValidatorIndexIncluded
      = !entryTypesVal
        || entryTypesVal.some(
          type => isWithdrawalEventType(type) || isEthBlockEventType(type) || isEthDepositEventType(type),
        );

    if (!disabled?.protocols && evmOrEthDepositEventsIncluded) {
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

    if (!disabled?.products && evmOrEthDepositEventsIncluded) {
      const products = get(historyEventProducts);
      data.push({
        description: t('transactions.filter.product'),
        key: HistoryEventFilterKeys.PRODUCT,
        keyValue: HistoryEventFilterValueKeys.PRODUCT,
        string: true,
        suggestions: () => products,
        validate: product => !!product,
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
          validate: (type: string) => !!type,
        });
      }

      let selectedEventTypes = get(filters)?.eventTypes || [];
      if (!Array.isArray(selectedEventTypes))
        selectedEventTypes = [selectedEventTypes.toString()];

      if (!disabled.eventSubtypes) {
        const globalMapping = get(historyEventTypeGlobalMapping);

        const globalMappingKeys: string[] = [];
        if (selectedEventTypes.length > 0) {
          selectedEventTypes.forEach((selectedEventType) => {
            const globalMappingFound = globalMapping[selectedEventType];
            if (globalMappingFound)
              globalMappingKeys.push(...Object.keys(globalMappingFound));
          });
        }
        else {
          for (const key in globalMapping)
            globalMappingKeys.push(...Object.keys(globalMapping[key]));
        }

        let selectedEventSubtypes = get(filters)?.eventSubtypes || [];
        if (!Array.isArray(selectedEventSubtypes))
          selectedEventSubtypes = [selectedEventSubtypes.toString()];

        if (selectedEventSubtypes.length > 0) {
          const filteredEventSubtypes = selectedEventSubtypes.filter(item => globalMappingKeys.includes(item));

          if (!isEqual(filteredEventSubtypes, selectedEventSubtypes)) {
            set(filters, {
              ...get(filters),
              eventSubtypes: filteredEventSubtypes.length > 0 ? filteredEventSubtypes : undefined,
            });
          }
        }

        data.push({
          description: t('transactions.filter.event_subtype'),
          key: HistoryEventFilterKeys.EVENT_SUBTYPE,
          keyValue: HistoryEventFilterValueKeys.EVENT_SUBTYPE,
          multiple: true,
          string: true,
          suggestions: () => globalMappingKeys.filter(uniqueStrings),
          validate: (type: string) => globalMappingKeys.includes(type),
        });
      }
    }

    if (evmOrEthDepositEventsIncluded) {
      data.push(
        {
          description: t('transactions.filter.tx_hash'),
          key: HistoryEventFilterKeys.TX_HASHES,
          keyValue: HistoryEventFilterValueKeys.TX_HASHES,
          multiple: true,
          string: true,
          suggestions: () => [],
          validate: (txHash: string) => isValidTxHash(txHash),
        },
        {
          description: t('transactions.filter.address'),
          key: HistoryEventFilterKeys.ADDRESSES,
          keyValue: HistoryEventFilterValueKeys.ADDRESSES,
          multiple: true,
          string: true,
          suggestions: () => [],
          validate: (address: string) => isValidEthAddress(address),
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
    [HistoryEventFilterValueKeys.ADDRESSES]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.ASSET]: OptionalString,
    [HistoryEventFilterValueKeys.END]: OptionalString,
    [HistoryEventFilterValueKeys.ENTRY_TYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.EVENT_SUBTYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.EVENT_TYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.LOCATION]: OptionalString,
    [HistoryEventFilterValueKeys.PRODUCT]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.PROTOCOL]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.START]: OptionalString,
    [HistoryEventFilterValueKeys.TX_HASHES]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.VALIDATOR_INDICES]: OptionalMultipleString,
  });

  return {
    filters,
    matchers,
    RouteFilterSchema,
  };
}
