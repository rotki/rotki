import { z } from 'zod';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type MaybeRef } from '@vueuse/core';
import {
  FilterBehaviour,
  type MatchedKeywordWithBehaviour,
  type SearchMatcher,
  assetDeserializer,
  assetSuggestions,
  dateDeserializer,
  dateSerializer,
  dateValidator
} from '@/types/filtering';
import {
  isEthBlockEventType,
  isEthDepositEventType,
  isEvmEventType,
  isWithdrawalEventType
} from '@/utils/history/events';

enum HistoryEventFilterKeys {
  START = 'start',
  END = 'end',
  ASSET = 'asset',
  PROTOCOL = 'protocol',
  EVENT_TYPE = 'event_type',
  LOCATION = 'location',
  ENTRY_TYPE = 'type',
  TX_HASHES = 'tx_hash',
  VALIDATOR_INDICES = 'validator_index'
}

enum HistoryEventFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
  ASSET = 'asset',
  PROTOCOL = 'counterparties',
  EVENT_TYPE = 'eventTypes',
  LOCATION = 'location',
  ENTRY_TYPE = 'entryTypes',
  TX_HASHES = 'txHashes',
  VALIDATOR_INDICES = 'validatorIndices'
}

export type Matcher = SearchMatcher<
  HistoryEventFilterKeys,
  HistoryEventFilterValueKeys
>;
export type Filters = MatchedKeywordWithBehaviour<HistoryEventFilterValueKeys>;

export const useHistoryEventFilter = (
  disabled: {
    protocols?: boolean;
    locations?: boolean;
  },
  entryTypes?: MaybeRef<HistoryEventEntryType[]>
) => {
  const filters: Ref<Filters> = ref({});

  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  const { counterparties } = useHistoryEventMappings();
  const { assetSearch } = useAssetInfoApi();
  const { assetInfo } = useAssetInfoRetrieval();
  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { tc } = useI18n();

  const matchers: ComputedRef<Matcher[]> = computed(() => {
    const data: Matcher[] = [
      {
        key: HistoryEventFilterKeys.START,
        keyValue: HistoryEventFilterValueKeys.START,
        description: tc('transactions.filter.start_date'),
        string: true,
        hint: tc('transactions.filter.date_hint', 0, {
          format: getDateInputISOFormat(get(dateInputFormat))
        }),
        suggestions: () => [],
        validate: dateValidator(dateInputFormat),
        serializer: dateSerializer(dateInputFormat),
        deserializer: dateDeserializer(dateInputFormat)
      },
      {
        key: HistoryEventFilterKeys.END,
        keyValue: HistoryEventFilterValueKeys.END,
        description: tc('transactions.filter.end_date'),
        string: true,
        hint: tc('transactions.filter.date_hint', 0, {
          format: getDateInputISOFormat(get(dateInputFormat))
        }),
        suggestions: () => [],
        validate: dateValidator(dateInputFormat),
        serializer: dateSerializer(dateInputFormat),
        deserializer: dateDeserializer(dateInputFormat)
      },
      {
        key: HistoryEventFilterKeys.ASSET,
        keyValue: HistoryEventFilterValueKeys.ASSET,
        description: tc('transactions.filter.asset'),
        asset: true,
        suggestions: assetSuggestions(assetSearch),
        deserializer: assetDeserializer(assetInfo)
      }
    ];

    const entryTypesVal = get(entryTypes);
    const evmOrEthDepositEventsIncluded =
      !entryTypesVal ||
      entryTypesVal.some(
        type => isEvmEventType(type) || isEthDepositEventType(type)
      );

    const eventsWithValidatorIndexIncluded =
      !entryTypesVal ||
      entryTypesVal.some(
        type =>
          isWithdrawalEventType(type) ||
          isEthBlockEventType(type) ||
          isEthDepositEventType(type)
      );

    if (!disabled?.protocols && evmOrEthDepositEventsIncluded) {
      data.push({
        key: HistoryEventFilterKeys.PROTOCOL,
        keyValue: HistoryEventFilterValueKeys.PROTOCOL,
        description: tc('transactions.filter.protocol'),
        multiple: true,
        string: true,
        suggestions: () => get(counterparties),
        validate: (protocol: string) => !!protocol
      });
    }

    if (!disabled?.locations) {
      data.push({
        key: HistoryEventFilterKeys.LOCATION,
        keyValue: HistoryEventFilterValueKeys.LOCATION,
        description: tc('transactions.filter.location'),
        string: true,
        suggestions: () => get(associatedLocations),
        validate: location => !!location
      });
    }

    if (!entryTypesVal || entryTypesVal.length > 0) {
      data.push({
        key: HistoryEventFilterKeys.ENTRY_TYPE,
        keyValue: HistoryEventFilterValueKeys.ENTRY_TYPE,
        description: tc('transactions.filter.entry_type'),
        string: true,
        multiple: true,
        suggestions: () =>
          entryTypesVal ?? Object.values(HistoryEventEntryType),
        validate: (type: string) => !!type,
        allowExclusion: true,
        behaviourRequired: true
      });
    }

    if (evmOrEthDepositEventsIncluded) {
      data.push({
        key: HistoryEventFilterKeys.TX_HASHES,
        keyValue: HistoryEventFilterValueKeys.TX_HASHES,
        description: tc('transactions.filter.tx_hash'),
        string: true,
        multiple: true,
        suggestions: () => [],
        validate: (txHash: string) => isValidTxHash(txHash)
      });
    }

    if (eventsWithValidatorIndexIncluded) {
      data.push({
        key: HistoryEventFilterKeys.VALIDATOR_INDICES,
        keyValue: HistoryEventFilterValueKeys.VALIDATOR_INDICES,
        description: tc('transactions.filter.validator_index'),
        string: true,
        multiple: true,
        suggestions: () => [],
        validate: (validatorIndex: string) => !!validatorIndex
      });
    }

    return data;
  });

  const updateFilter = (newFilters: Filters) => {
    set(filters, {
      ...newFilters
    });
  };

  const OptionalString = z.string().optional();
  const OptionalMultipleString = z
    .array(z.string())
    .or(z.string())
    .transform(val => (Array.isArray(val) ? val : [val]))
    .optional();

  const RouteFilterSchema = z.object({
    [HistoryEventFilterValueKeys.START]: OptionalString,
    [HistoryEventFilterValueKeys.END]: OptionalString,
    [HistoryEventFilterValueKeys.ASSET]: OptionalString,
    [HistoryEventFilterValueKeys.PROTOCOL]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.LOCATION]: OptionalString,
    [HistoryEventFilterValueKeys.ENTRY_TYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.TX_HASHES]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.VALIDATOR_INDICES]: OptionalMultipleString
  });

  const transformFilters = (filters: Filters): Filters => {
    const matchersVal: Matcher[] = get(matchers).filter(
      item => 'string' in item && item.behaviourRequired
    );

    const newFilters: Filters = { ...filters };
    matchersVal.forEach(matcher => {
      if (!('string' in matcher)) {
        return;
      }
      const keyValue = matcher.keyValue;
      if (keyValue && keyValue in filters) {
        const data = filters[keyValue];
        if (!data) {
          return;
        }

        if (typeof data === 'object' && !Array.isArray(data)) {
          if (data.values) {
            newFilters[keyValue] = {
              behaviour: data.behaviour ?? FilterBehaviour.INCLUDE,
              values: data.values
            };
          }
          return;
        }

        let formattedData: string | string[] = data;
        let exclude = false;

        if (matcher.allowExclusion) {
          if (typeof data === 'string' && data.startsWith('!')) {
            exclude = true;
            formattedData = data.substring(1);
          } else if (
            Array.isArray(data) &&
            data.length > 0 &&
            data[0].startsWith('!')
          ) {
            exclude = true;
            formattedData = data.map(item =>
              item.startsWith('!') ? item.substring(1) : item
            );
          }
        }

        newFilters[keyValue] = {
          behaviour: exclude
            ? FilterBehaviour.EXCLUDE
            : FilterBehaviour.INCLUDE,
          values: formattedData
        };
      }
    });

    return newFilters;
  };

  return {
    matchers,
    filters,
    updateFilter,
    transformFilters,
    RouteFilterSchema
  };
};
