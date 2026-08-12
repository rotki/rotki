import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef, ValueIcon } from '@/modules/core/table/pill/core/types';
import { HistoryEventEntryType, isValidTxHashOrSignature } from '@rotki/common';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { type AccountFieldOptions, toAccountField } from '@/modules/core/table/filters/shared/account-field';
import { toAssetField } from '@/modules/core/table/filters/shared/asset-field';
import { toPeriodField } from '@/modules/core/table/filters/shared/period-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toMatchFieldDef, toParamFieldDef, toRangeFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import {
  isBitcoinEventType,
  isEthBlockEventType,
  isEthDepositEventType,
  isEvmEventType,
  isOnlineHistoryEventType,
  isSolanaEventType,
  isWithdrawalEventType,
} from '@/modules/history/event-utils';
import { HistoryEventFilterKeys } from '@/modules/history/events/use-events-filter';

type Translate = (key: string) => string;

/**
 * What history needs on top of the shared resolution every pill-bar table gets: the two mapping
 * lookups that only history events have.
 */
export interface HistoryFieldResolvers extends SharedFieldResolvers {
  readonly t: Translate;
  /** Raw event type (e.g. `informational`) -> its display name. */
  readonly resolveEventTypeName: (value: string) => string;
  /** Raw event subtype (e.g. `receive_wrapped`) -> its display name. */
  readonly resolveEventSubTypeName: (value: string) => string;
}

/**
 * Which fields the view has already decided for the user, so the bar does not offer them again: a
 * page pinned to one protocol, one location, one period, one set of validators or event types has
 * nothing left to narrow there.
 */
export interface HistoryEventFieldGates {
  readonly protocols?: boolean;
  readonly locations?: boolean;
  readonly period?: boolean;
  readonly validators?: boolean;
  readonly eventTypes?: boolean;
  readonly eventSubtypes?: boolean;
}

/** What the history event fields need from the Vue layer to be built. */
export interface HistoryEventFieldOptions {
  readonly disabled: HistoryEventFieldGates;
  /**
   * The entry types the view is restricted to, absent when every kind of event is in play. It
   * decides both what the entry-type pill offers and which of the other fields make sense at all.
   */
  readonly entryTypes: HistoryEventEntryType[] | undefined;
  readonly counterparties: () => string[];
  readonly locations: () => string[];
  readonly eventTypes: () => string[];
  /** The subtypes the selected event types admit, already narrowed and deduplicated. */
  readonly eventSubtypes: () => string[];
  /**
   * The same lookup as a function of the types, rather than of the current selection: what the
   * subtype field `admits` is asked for the types the bar is about to hold, not the ones it holds.
   */
  readonly subtypesFor: (eventTypes: readonly string[]) => string[];
  /** The async asset search, already scoped to the picked location. */
  readonly searchAsset: (value: string) => Promise<AssetsWithId>;
}

/**
 * Which families of event the current entry-type restriction admits. An absent restriction means
 * every family is in play, so each flag defaults to true.
 */
interface IncludedEventKinds {
  transactions: boolean;
  evmOrOnline: boolean;
  validatorIndex: boolean;
}

function resolveIncludedKinds(entryTypes: HistoryEventEntryType[] | undefined): IncludedEventKinds {
  if (!entryTypes)
    return { evmOrOnline: true, transactions: true, validatorIndex: true };

  return {
    evmOrOnline: entryTypes.some(type => isEvmEventType(type) || isOnlineHistoryEventType(type)),
    transactions: entryTypes.some(type => isEvmEventType(type) || isEthDepositEventType(type) || isSolanaEventType(type) || isBitcoinEventType(type)),
    validatorIndex: entryTypes.some(type => isWithdrawalEventType(type) || isEthBlockEventType(type) || isEthDepositEventType(type)),
  };
}

/** The action pill is the same two request keys under one verb, so it cannot sit beside these. */
const EXCLUDES_ACTION: readonly string[] = ['action'];

/** The period, and the two amount bounds, as the single pills they read as on screen. */
function boundsFields(resolvers: HistoryFieldResolvers, options: HistoryEventFieldOptions): FieldDef[] {
  const { t } = resolvers;
  const period = options.disabled.period
    ? []
    : [toPeriodField(
        (): string => t('transactions.filter_field_labels.period'),
        {
          // The one table here whose timestamp column is milliseconds: the backend scales both
          // bounds by 1000 (`HistoryBaseEntryFilterQuery`), so an equal pair asks for the single
          // millisecond `X000` and drops every other event in the second the user picked.
          allowEqual: false,
          lowerKey: HistoryEventFilterKeys.START,
          upperKey: HistoryEventFilterKeys.END,
        },
        resolvers,
      )];

  return [
    ...period,
    toAssetField({
      key: HistoryEventFilterKeys.ASSET,
      label: (): string => t('transactions.filter_field_labels.asset'),
      searchAsset: options.searchAsset,
    }, resolvers),
    // The backend matches a substring of the notes, so what the user writes is the value.
    toMatchFieldDef({
      freeText: true,
      key: HistoryEventFilterKeys.NOTES,
      label: (): string => t('transactions.filter_field_labels.notes'),
      multiple: false,
      validate: (notes: string): boolean => !!notes,
    }),
    toRangeFieldDef({
      key: 'amount',
      label: (): string => t('transactions.filter_field_labels.amount'),
      lowerKey: HistoryEventFilterKeys.MIN_AMOUNT,
      upperKey: HistoryEventFilterKeys.MAX_AMOUNT,
    }),
  ];
}

/** Where an event happened: the protocol it went through and the location it is held at. */
function venueFields(
  resolvers: HistoryFieldResolvers,
  options: HistoryEventFieldOptions,
  included: IncludedEventKinds,
): FieldDef[] {
  const { t } = resolvers;
  const fields: FieldDef[] = [];

  if (!options.disabled.protocols && included.transactions) {
    fields.push(decorateSharedField(
      toMatchFieldDef({
        key: HistoryEventFilterKeys.PROTOCOL,
        label: (): string => t('transactions.filter_field_labels.protocol'),
        multiple: true,
        suggest: options.counterparties,
      }),
      SharedFieldKinds.PROTOCOL,
      resolvers,
    ));
  }

  if (!options.disabled.locations) {
    fields.push(decorateSharedField(
      toMatchFieldDef({
        key: HistoryEventFilterKeys.LOCATION,
        label: (): string => t('transactions.filter_field_labels.location'),
        multiple: false,
        suggest: options.locations,
      }),
      SharedFieldKinds.LOCATION,
      resolvers,
    ));
  }

  return fields;
}

/** What kind of event it is: its entry type, and the type/subtype pair the app classifies it by. */
function classificationFields(
  resolvers: HistoryFieldResolvers,
  options: HistoryEventFieldOptions,
  included: IncludedEventKinds,
): FieldDef[] {
  const { t } = resolvers;
  const { disabled, entryTypes } = options;
  const fields: FieldDef[] = [];

  // With the choice already narrowed to a single type there is nothing to filter by.
  if (!entryTypes || entryTypes.length > 1) {
    fields.push(decorateSharedField(
      toMatchFieldDef({
        // The one excludable field in the app: the request takes entry types as
        // `{ behaviour, values }`, which is what lets a type be filtered out rather than in.
        allowExclusion: true,
        key: HistoryEventFilterKeys.ENTRY_TYPE,
        label: (): string => t('transactions.filter_field_labels.entry_type'),
        multiple: true,
        suggest: (): string[] => entryTypes ?? Object.values(HistoryEventEntryType),
      }),
      SharedFieldKinds.TOKEN,
      resolvers,
    ));
  }

  if (included.evmOrOnline && !disabled.eventTypes) {
    fields.push(toMatchFieldDef({
      excludes: EXCLUDES_ACTION,
      key: HistoryEventFilterKeys.EVENT_TYPE,
      label: (): string => t('transactions.filter_field_labels.event_type'),
      multiple: true,
      // Looked up in mappings no other table carries, so a pill reads as its rows do.
      resolveLabel: resolvers.resolveEventTypeName,
      suggest: options.eventTypes,
    }));
  }

  if (included.evmOrOnline && !disabled.eventSubtypes) {
    fields.push(toMatchFieldDef({
      // The backend reads types and subtypes as a cross product, so a subtype the selected types do
      // not admit matches nothing. The bar narrows what can be added, drops what stops being
      // admitted, and refuses it if typed — all three off the one mapping lookup.
      admits: values => options.subtypesFor(values[HistoryEventFilterKeys.EVENT_TYPE] ?? []),
      excludes: EXCLUDES_ACTION,
      key: HistoryEventFilterKeys.EVENT_SUBTYPE,
      label: (): string => t('transactions.filter_field_labels.event_subtype'),
      multiple: true,
      resolveLabel: resolvers.resolveEventSubTypeName,
      suggest: options.eventSubtypes,
      validate: (subtype: string): boolean => options.eventSubtypes().includes(subtype),
    }));
  }

  return fields;
}

/** What an event can be traced by: its transaction, the address on it, or the validator it is for. */
function traceFields(
  resolvers: HistoryFieldResolvers,
  options: HistoryEventFieldOptions,
  included: IncludedEventKinds,
): FieldDef[] {
  const { t } = resolvers;
  const fields: FieldDef[] = [];

  if (included.transactions) {
    fields.push(
      decorateSharedField(
        toMatchFieldDef({
          invalidHint: (): string => t('transactions.filter.invalid_tx_hash'),
          key: HistoryEventFilterKeys.TX_HASHES,
          label: (): string => t('transactions.filter_field_labels.tx_hash'),
          multiple: true,
          // A signature counts too, which is why this is not the shared hex check.
          validate: (txHash: string): boolean => isValidTxHashOrSignature(txHash),
        }),
        SharedFieldKinds.TX_HASH,
        resolvers,
      ),
      // The address kind carries the typing, the shortening and the validation.
      decorateSharedField(
        toMatchFieldDef({
          invalidHint: (): string => t('transactions.filter.invalid_address'),
          key: HistoryEventFilterKeys.ADDRESSES,
          label: (): string => t('transactions.filter_field_labels.address'),
          multiple: true,
        }),
        SharedFieldKinds.ADDRESS,
        resolvers,
      ),
    );
  }

  if (included.validatorIndex && !options.disabled.validators) {
    fields.push(toMatchFieldDef({
      freeText: true,
      invalidHint: (): string => t('transactions.filter.invalid_validator_index'),
      key: HistoryEventFilterKeys.VALIDATOR_INDICES,
      label: (): string => t('transactions.filter_field_labels.validator_index'),
      multiple: true,
      validate: (validatorIndex: string): boolean => /^\d+$/.test(validatorIndex),
    }));
  }

  return fields;
}

/**
 * The pill-bar fields history events sends in its filter bag.
 *
 * Each group states its own gates and contributes nothing when they do not apply, so the order here
 * is the display order.
 */
export function toHistoryEventFields(
  resolvers: HistoryFieldResolvers,
  options: HistoryEventFieldOptions,
): FieldDef[] {
  const included = resolveIncludedKinds(options.entryTypes);

  return [
    ...boundsFields(resolvers, options),
    ...venueFields(resolvers, options, included),
    ...classificationFields(resolvers, options, included),
    ...traceFields(resolvers, options, included),
  ];
}

/**
 * The history account filter (tracked-address `locationLabels`) as a param-bound pill field. It
 * lives outside `toHistoryEventFields` because it is an external filter, not a matcher, and is
 * only offered when the view is not already pinned to an external account set.
 */
/**
 * The history event state markers (matched / customized / imported / profit adjustment /
 * synthetic) as a param-bound pill field. Like the account field it is an external filter rather
 * than a matcher: it rides the `stateMarkers` param, which goes to both the request and the URL.
 *
 * Its values are read by their glyph and colour in the list it came from, so unlike the other
 * non-identity enums it keeps a per-value icon (`resolveIcon`).
 */
export function toHistoryStateField(
  t: Translate,
  states: string[],
  resolveLabel: (value: string) => string,
  resolveIcon: (value: string) => ValueIcon | undefined,
): FieldDef {
  return toParamFieldDef({
    key: 'state',
    label: (): string => t('transactions.filter_field_labels.state'),
    multiple: true,
    paramKey: 'stateMarkers',
    resolveIcon,
    resolveLabel,
    suggest: () => states,
    to: 'both',
  });
}

/**
 * The show-ignored-assets toggle as a param-bound boolean pill. A boolean field has no editor and
 * no value segment: adding the pill turns it on, removing it turns it off, which is the whole of
 * its state. The wire form stays inverted (`excludeIgnoredAssets`), handled by the param source.
 */
export function toHistoryIgnoredField(t: Translate): FieldDef {
  return toParamFieldDef({
    key: 'ignored',
    label: (): string => t('transactions.filter_field_labels.show_ignored'),
    multiple: false,
    paramKey: 'showIgnoredAssets',
    to: 'both',
    valueType: FilterValueTypes.BOOLEAN,
  });
}

/** One selectable action: a verb standing for exactly one event type/subtype pair. */
export interface ActionFieldOption {
  readonly verbKey: string;
  readonly label: string;
  readonly icon: ValueIcon;
}

/**
 * The event action (verb) as a param-bound pill. An action is one presentation of a single
 * `(eventType, eventSubtype)` pair — the same pairing the event form's action picker uses — so it
 * writes no wire filter of its own: the param source expands the verb into those two request keys.
 * The URL carries only the verb, which is what keeps the user's intent across a reload. Rebuilding
 * from raw types would lose whether they picked an action or set the two fields by hand.
 *
 * It excludes Type and Subtype, and they exclude it: all three drive the same two request keys.
 */
export function toHistoryActionField(t: Translate, actions: () => ActionFieldOption[]): FieldDef {
  // Computed, not a getter that rebuilds. `resolveLabel` and `resolveIcon` are called once per
  // candidate value while the bar narrows, so rebuilding the map inside them cost a full pass over
  // the actions for every value examined - quadratic in the number of verbs, on every keystroke,
  // and every object it allocated was thrown away immediately.
  const byVerb = computed<Map<string, ActionFieldOption>>(
    () => new Map(actions().map(action => [action.verbKey, action])),
  );
  const verbKeys = computed<string[]>(() => actions().map(action => action.verbKey));
  return toParamFieldDef({
    excludes: [HistoryEventFilterKeys.EVENT_TYPE, HistoryEventFilterKeys.EVENT_SUBTYPE],
    key: 'action',
    label: (): string => t('transactions.filter_field_labels.action'),
    multiple: false,
    paramKey: 'action',
    resolveIcon: (value: string): ValueIcon | undefined => get(byVerb).get(value)?.icon,
    resolveLabel: (value: string): string => get(byVerb).get(value)?.label ?? value,
    suggest: (): string[] => get(verbKeys),
    to: 'url',
  });
}

/**
 * History's account pill: the shared account field bound to the `locationLabels` request param.
 */
export function toHistoryAccountField(t: Translate, accounts: AccountFieldOptions): FieldDef {
  return toAccountField(
    { label: (): string => t('transactions.filter_field_labels.account'), paramKey: 'locationLabels', to: 'request' },
    accounts,
  );
}
