import type { MaybeRef } from 'vue';
import type {
  MatchedKeywordWithBehaviour,
  SearchMatcher,
} from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import {
  HistoryEventEntryType,
  isValidAddress,
  isValidTxHashOrSignature,
} from '@rotki/common';
import { z } from 'zod';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { arrayify } from '@/modules/core/common/data/array';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { dateDeserializer, dateRangeValidator, dateSerializer, getDateInputISOFormat } from '@/modules/core/common/data/date';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { useEventSubtypeKeys } from '@/modules/core/table/filters/use-event-subtype-keys';
import {
  isEthBlockEventType,
  isEthDepositEventType,
  isEvmEventType,
  isOnlineHistoryEventType,
  isSolanaEventType,
  isWithdrawalEventType,
} from '@/modules/history/event-utils';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { useSetting } from '@/modules/settings/use-setting';

export enum HistoryEventFilterKeys {
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
  MIN_AMOUNT = 'min_amount',
  MAX_AMOUNT = 'max_amount',
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
  MIN_AMOUNT = 'minAmount',
  MAX_AMOUNT = 'maxAmount',
}

export type Matcher = SearchMatcher<HistoryEventFilterKeys, HistoryEventFilterValueKeys>;

function amountRangeValidator(
  otherBound: () => string | undefined,
  bound: 'min' | 'max',
): (amount: string) => boolean {
  return (amount: string): boolean => {
    const parsed = Number(amount);
    if (!amount || Number.isNaN(parsed) || parsed < 0)
      return false;

    const other = otherBound();
    if (other === undefined)
      return true;

    const otherParsed = Number(other);
    if (Number.isNaN(otherParsed))
      return true;

    return bound === 'min' ? parsed <= otherParsed : parsed >= otherParsed;
  };
}

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
  const modelFilters = ref<Filters>({});

  const dateInputFormat = useSetting('dateInputFormat');
  const { historyEventTypeGlobalMapping, historyEventTypes } = useHistoryEventMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { assetSearch, getAssetInfo } = useAssetInfoRetrieval();
  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { t } = useI18n({ useScope: 'global' });

  const validSubtypeKeys = useEventSubtypeKeys({
    disabled: () => disabled.eventSubtypes,
    globalMapping: historyEventTypeGlobalMapping,
    modelFilters,
  });

  /**
   * Which families of event the current entry-type restriction admits. An absent restriction means
   * every family is in play, so each flag defaults to true.
   */
  interface IncludedEventKinds {
    transactions: boolean;
    evmOrOnline: boolean;
    validatorIndex: boolean;
  }

  function resolveIncludedKinds(entryTypesVal: HistoryEventEntryType[] | undefined): IncludedEventKinds {
    if (!entryTypesVal)
      return { evmOrOnline: true, transactions: true, validatorIndex: true };

    return {
      evmOrOnline: entryTypesVal.some(type => isEvmEventType(type) || isOnlineHistoryEventType(type)),
      transactions: entryTypesVal.some(type => isEvmEventType(type) || isEthDepositEventType(type) || isSolanaEventType(type)),
      validatorIndex: entryTypesVal.some(type => isWithdrawalEventType(type) || isEthBlockEventType(type) || isEthDepositEventType(type)),
    };
  }

  function dateMatchers(): Matcher[] {
    if (disabled?.period)
      return [];

    const hint = t('transactions.filter.date_hint', {
      format: getDateInputISOFormat(get(dateInputFormat)),
    });

    return [
      {
        description: t('transactions.filter.start_date'),
        deserializer: dateDeserializer(dateInputFormat),
        hint,
        key: HistoryEventFilterKeys.START,
        keyValue: HistoryEventFilterValueKeys.START,
        serializer: dateSerializer(dateInputFormat),
        string: true,
        suggestions: () => [],
        validate: dateRangeValidator(dateInputFormat, () => get(modelFilters)?.toTimestamp?.toString(), 'start'),
      },
      {
        description: t('transactions.filter.end_date'),
        deserializer: dateDeserializer(dateInputFormat),
        hint,
        key: HistoryEventFilterKeys.END,
        keyValue: HistoryEventFilterValueKeys.END,
        serializer: dateSerializer(dateInputFormat),
        string: true,
        suggestions: () => [],
        validate: dateRangeValidator(dateInputFormat, () => get(modelFilters)?.fromTimestamp?.toString(), 'end'),
      },
    ];
  }

  function coreMatchers(locationString: string | undefined): Matcher[] {
    return [
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
      {
        description: t('transactions.filter.min_amount'),
        key: HistoryEventFilterKeys.MIN_AMOUNT,
        keyValue: HistoryEventFilterValueKeys.MIN_AMOUNT,
        string: true,
        suggestions: () => [],
        validate: amountRangeValidator(() => get(modelFilters)?.maxAmount?.toString(), 'min'),
      },
      {
        description: t('transactions.filter.max_amount'),
        key: HistoryEventFilterKeys.MAX_AMOUNT,
        keyValue: HistoryEventFilterValueKeys.MAX_AMOUNT,
        string: true,
        suggestions: () => [],
        validate: amountRangeValidator(() => get(modelFilters)?.minAmount?.toString(), 'max'),
      },
    ];
  }

  function protocolMatchers(included: IncludedEventKinds): Matcher[] {
    if (disabled?.protocols || !included.transactions)
      return [];

    const counterpartiesVal = get(counterparties);
    return [{
      description: t('transactions.filter.protocol'),
      key: HistoryEventFilterKeys.PROTOCOL,
      keyValue: HistoryEventFilterValueKeys.PROTOCOL,
      multiple: true,
      string: true,
      suggestions: () => counterpartiesVal,
      validate: (protocol: string) => !!protocol,
    }];
  }

  function locationMatchers(): Matcher[] {
    if (disabled?.locations)
      return [];

    return [{
      description: t('transactions.filter.location'),
      key: HistoryEventFilterKeys.LOCATION,
      keyValue: HistoryEventFilterValueKeys.LOCATION,
      string: true,
      suggestions: () => get(associatedLocations),
      validate: location => !!location,
    }];
  }

  function entryTypeMatchers(entryTypesVal: HistoryEventEntryType[] | undefined): Matcher[] {
    // With the choice already narrowed to a single type there is nothing to filter by.
    if (entryTypesVal && entryTypesVal.length <= 1)
      return [];

    return [{
      allowExclusion: true,
      behaviourRequired: true,
      description: t('transactions.filter.entry_type'),
      key: HistoryEventFilterKeys.ENTRY_TYPE,
      keyValue: HistoryEventFilterValueKeys.ENTRY_TYPE,
      multiple: true,
      string: true,
      suggestions: () => entryTypesVal ?? Object.values(HistoryEventEntryType),
      validate: (type: string) => !!type,
    }];
  }

  function eventTypeMatchers(included: IncludedEventKinds): Matcher[] {
    if (!included.evmOrOnline)
      return [];

    const data: Matcher[] = [];

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

    return data;
  }

  function transactionMatchers(included: IncludedEventKinds): Matcher[] {
    if (!included.transactions)
      return [];

    return [
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
    ];
  }

  function validatorMatchers(included: IncludedEventKinds): Matcher[] {
    if (!included.validatorIndex || disabled?.validators)
      return [];

    return [{
      description: t('transactions.filter.validator_index'),
      key: HistoryEventFilterKeys.VALIDATOR_INDICES,
      keyValue: HistoryEventFilterValueKeys.VALIDATOR_INDICES,
      multiple: true,
      string: true,
      suggestions: () => [],
      validate: (validatorIndex: string) => !!validatorIndex,
    }];
  }

  // Each builder owns its own gate and returns nothing when it does not apply, so the order here is
  // the display order and this stays a plain concatenation.
  const matchers = computed<Matcher[]>(() => {
    const selectedLocation = get(modelFilters)?.location;
    const locationString = (Array.isArray(selectedLocation) ? selectedLocation[0] : selectedLocation)?.toString();
    const entryTypesVal = get(entryTypes);
    const included = resolveIncludedKinds(entryTypesVal);

    return [
      ...dateMatchers(),
      ...coreMatchers(locationString),
      ...protocolMatchers(included),
      ...locationMatchers(),
      ...entryTypeMatchers(entryTypesVal),
      ...eventTypeMatchers(included),
      ...transactionMatchers(included),
      ...validatorMatchers(included),
    ];
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
    [HistoryEventFilterValueKeys.MAX_AMOUNT]: OptionalString,
    [HistoryEventFilterValueKeys.MIN_AMOUNT]: OptionalString,
    [HistoryEventFilterValueKeys.NOTES]: OptionalString,
    [HistoryEventFilterValueKeys.PROTOCOL]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.TX_HASHES]: OptionalMultipleString,
    [HistoryEventFilterValueKeys.VALIDATOR_INDICES]: OptionalMultipleString,
  });

  return {
    filters: modelFilters,
    matchers,
    RouteFilterSchema,
  };
}
