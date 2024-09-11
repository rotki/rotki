import { z } from 'zod';
import { HistoryEventEntryType } from '@rotki/common';
import { isEqual } from 'lodash-es';
import {
  type MatchedKeywordWithBehaviour,
  type SearchMatcher,
  assetDeserializer,
  assetSuggestions,
  dateDeserializer,
  dateSerializer,
  dateValidator,
} from '@/types/filtering';
import type { MaybeRef } from '@vueuse/core';
import type { FilterSchema } from '@/composables/filter-paginate';

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
  const { historyEventTypes, historyEventTypeGlobalMapping } = useHistoryEventMappings();
  const { historyEventProducts } = useHistoryEventProductMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { assetSearch, assetInfo } = useAssetInfoRetrieval();
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
              key: HistoryEventFilterKeys.START,
              keyValue: HistoryEventFilterValueKeys.START,
              description: t('transactions.filter.start_date'),
              string: true,
              hint: t('transactions.filter.date_hint', {
                format: getDateInputISOFormat(get(dateInputFormat)),
              }),
              suggestions: () => [],
              validate: dateValidator(dateInputFormat),
              serializer: dateSerializer(dateInputFormat),
              deserializer: dateDeserializer(dateInputFormat),
            },
            {
              key: HistoryEventFilterKeys.END,
              keyValue: HistoryEventFilterValueKeys.END,
              description: t('transactions.filter.end_date'),
              string: true,
              hint: t('transactions.filter.date_hint', {
                format: getDateInputISOFormat(get(dateInputFormat)),
              }),
              suggestions: () => [],
              validate: dateValidator(dateInputFormat),
              serializer: dateSerializer(dateInputFormat),
              deserializer: dateDeserializer(dateInputFormat),
            },
          ] satisfies Matcher[])),
      {
        key: HistoryEventFilterKeys.ASSET,
        keyValue: HistoryEventFilterValueKeys.ASSET,
        description: t('transactions.filter.asset'),
        asset: true,
        suggestions: assetSuggestions(assetSearch, selectedLocation?.toString()),
        deserializer: assetDeserializer(assetInfo),
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
        key: HistoryEventFilterKeys.PROTOCOL,
        keyValue: HistoryEventFilterValueKeys.PROTOCOL,
        description: t('transactions.filter.protocol'),
        multiple: true,
        string: true,
        suggestions: () => counterpartiesVal,
        validate: (protocol: string) => !!protocol,
      });
    }

    if (!disabled?.locations) {
      data.push({
        key: HistoryEventFilterKeys.LOCATION,
        keyValue: HistoryEventFilterValueKeys.LOCATION,
        description: t('transactions.filter.location'),
        string: true,
        suggestions: () => get(associatedLocations),
        validate: location => !!location,
      });
    }

    if (!disabled?.products && evmOrEthDepositEventsIncluded) {
      const products = get(historyEventProducts);
      data.push({
        key: HistoryEventFilterKeys.PRODUCT,
        keyValue: HistoryEventFilterValueKeys.PRODUCT,
        description: t('transactions.filter.product'),
        string: true,
        suggestions: () => products,
        validate: product => !!product,
      });
    }

    if (!entryTypesVal || entryTypesVal.length > 1) {
      data.push({
        key: HistoryEventFilterKeys.ENTRY_TYPE,
        keyValue: HistoryEventFilterValueKeys.ENTRY_TYPE,
        description: t('transactions.filter.entry_type'),
        string: true,
        multiple: true,
        suggestions: () => entryTypesVal ?? Object.values(HistoryEventEntryType),
        validate: (type: string) => !!type,
        allowExclusion: true,
        behaviourRequired: true,
      });
    }

    if (evmOrOnlineEventsIncluded) {
      if (!disabled.eventTypes) {
        data.push({
          key: HistoryEventFilterKeys.EVENT_TYPE,
          keyValue: HistoryEventFilterValueKeys.EVENT_TYPE,
          description: t('transactions.filter.event_type'),
          string: true,
          multiple: true,
          suggestions: () => get(historyEventTypes),
          validate: (type: string) => !!type,
        });
      }

      let selectedEventTypes = get(filters)?.eventTypes || [];
      if (!Array.isArray(selectedEventTypes))
        selectedEventTypes = [`${selectedEventTypes}`];

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
          selectedEventSubtypes = [`${selectedEventSubtypes}`];

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
          key: HistoryEventFilterKeys.EVENT_SUBTYPE,
          keyValue: HistoryEventFilterValueKeys.EVENT_SUBTYPE,
          description: t('transactions.filter.event_subtype'),
          string: true,
          multiple: true,
          suggestions: () => globalMappingKeys.filter(uniqueStrings),
          validate: (type: string) => globalMappingKeys.includes(type),
        });
      }
    }

    if (evmOrEthDepositEventsIncluded) {
      data.push(
        {
          key: HistoryEventFilterKeys.TX_HASHES,
          keyValue: HistoryEventFilterValueKeys.TX_HASHES,
          description: t('transactions.filter.tx_hash'),
          string: true,
          multiple: true,
          suggestions: () => [],
          validate: (txHash: string) => isValidTxHash(txHash),
        },
        {
          key: HistoryEventFilterKeys.ADDRESSES,
          keyValue: HistoryEventFilterValueKeys.ADDRESSES,
          description: t('transactions.filter.address'),
          string: true,
          multiple: true,
          suggestions: () => [],
          validate: (address: string) => isValidEthAddress(address),
        },
      );
    }

    if (eventsWithValidatorIndexIncluded && !disabled?.validators) {
      data.push({
        key: HistoryEventFilterKeys.VALIDATOR_INDICES,
        keyValue: HistoryEventFilterValueKeys.VALIDATOR_INDICES,
        description: t('transactions.filter.validator_index'),
        string: true,
        multiple: true,
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
    [HistoryEventFilterValueKeys.ASSET]: OptionalString,
    [HistoryEventFilterValueKeys.PROTOCOL]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.PRODUCT]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.LOCATION]: OptionalString,
    [HistoryEventFilterValueKeys.ENTRY_TYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.EVENT_TYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.EVENT_SUBTYPE]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.TX_HASHES]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.ADDRESSES]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.VALIDATOR_INDICES]: OptionalMultipleString,
  });

  return {
    matchers,
    filters,
    RouteFilterSchema,
  };
}
