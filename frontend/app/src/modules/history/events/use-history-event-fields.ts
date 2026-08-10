import type { HistoryEventEntryType } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AssetsWithId } from '@/modules/assets/types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useEventActionPicker } from '@/modules/history/events/action-picker/use-event-action-picker';
import { type ActionFieldOption, toHistoryAccountField, toHistoryActionField, toHistoryEventFields, toHistoryIgnoredField, toHistoryStateField } from '@/modules/history/events/history-event-fields';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { isValidHistoryEventState, useHistoryEventStateMapping } from '@/modules/history/events/mapping/use-history-event-state-mapping';
import { HistoryEventState } from '@/modules/history/events/schemas';
import { useAccountFilterOptions } from '@/modules/history/use-account-filter-options';
import { useHistoryStore } from '@/modules/history/use-history-store';

/**
 * What the view has already decided for the user. It is the same object the table's own filters
 * take, so a page states its restrictions once and both read them: a page pinned to one protocol,
 * location, period, validator set or event type has nothing left to offer a pill for.
 */
export interface HistoryEventFieldsOptions {
  entryTypes: MaybeRefOrGetter<HistoryEventEntryType[] | undefined>;
  /**
   * The table's filter bag, writable: what is picked scopes the asset search and the offered
   * subtypes, and a narrowing subtype set prunes what it no longer admits.
   */
  modelFilters: Ref<Filters>;
  eventSubTypes: MaybeRefOrGetter<string[]>;
  eventTypes: MaybeRefOrGetter<string[]>;
  location: MaybeRefOrGetter<string | undefined>;
  period: MaybeRefOrGetter<unknown>;
  protocols: MaybeRefOrGetter<string[]>;
  /** True when the view is pinned to an external account set, which replaces the account pill. */
  useExternalAccountFilter: MaybeRefOrGetter<boolean | undefined>;
  validators: MaybeRefOrGetter<number[] | undefined>;
}

/**
 * Assembles the pill-bar `FieldDef`s for history events: the fields it sends in its filter bag plus
 * the external param pills — action, state markers, ignored assets and account (`locationLabels`).
 * The account pill is omitted when the view is already pinned to an external account set.
 */
export function useHistoryEventFields(options: HistoryEventFieldsOptions): ComputedRef<FieldDef[]> {
  const { entryTypes, modelFilters: filters, useExternalAccountFilter } = options;

  // What the view fixes, and so the bar does not offer.
  const disabled = computed(() => ({
    eventSubtypes: (toValue(options.eventSubTypes) || []).length > 0,
    eventTypes: (toValue(options.eventTypes) || []).length > 0,
    locations: !!toValue(options.location),
    period: !!toValue(options.period),
    protocols: (toValue(options.protocols) || []).length > 0,
    validators: !!toValue(options.validators),
  }));

  const { t } = useI18n({ useScope: 'global' });
  const { getHistoryEventSubTypeName, getHistoryEventTypeName, historyEventTypeGlobalMapping, historyEventTypes } = useHistoryEventMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { options: accountOptions, resolveCaption, resolveLabel } = useAccountFilterOptions();
  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { assetSearch } = useAssetInfoRetrieval();
  const { stateConfigs } = useHistoryEventStateMapping();
  // The bar offers the same verbs the event form's action picker does, from the same model, so a
  // filter and an edit speak of events in one vocabulary.
  const { rows: actionRows } = useEventActionPicker();
  // Asset, location, protocol, address and date resolution is the same for every table that
  // filters on them, so it comes from one place rather than being restated here.
  const shared = useSharedFieldResolvers();

  /**
   * The subtypes a set of event types admits, deduplicated; every known subtype when no type is
   * picked. The field declares it twice over — as the option list it offers, and as what it
   * `admits` — so the narrowing and the pruning of an already-picked subtype cannot disagree.
   */
  function subtypesFor(eventTypes: readonly string[]): string[] {
    const mapping = get(historyEventTypeGlobalMapping);
    if (Object.keys(mapping).length === 0)
      return [];

    const keys = eventTypes.length === 0
      ? Object.values(mapping).flatMap(entry => Object.keys(entry))
      : eventTypes.flatMap(selected => Object.keys(mapping[selected] ?? {}));

    return keys.filter(uniqueStrings);
  }

  const selectedEventTypes = computed<string[]>(() => {
    const picked = get(filters)?.eventTypes;
    if (picked === undefined)
      return [];

    return (Array.isArray(picked) ? picked : [picked]).map(entry => entry.toString());
  });

  /**
   * The asset search is scoped to the picked location, so a location that names a chain searches
   * that chain's assets. The filter holds one location but the bag types it as one-or-many.
   */
  const location = computed<string | undefined>(() => {
    const picked = get(filters)?.location;
    return (Array.isArray(picked) ? picked[0] : picked)?.toString();
  });

  // One debounced search per scope rather than one per call: `assetSuggestions` builds the
  // debounce, so rebuilding it inside the search would give every keystroke a fresh timer that
  // cancels nothing.
  const search = computed(() => assetSuggestions(assetSearch, get(location)));
  const searchAsset = async (value: string): Promise<AssetsWithId> => get(search)(value);

  // The option list already carries `address name tags` per account for its own search box; the
  // bar reuses it so an account is findable by any of them from the inline input too.
  const accountKeywords = computed<Map<string, string | undefined>>(
    () => new Map(get(accountOptions).map(option => [option.value, option.keywords])),
  );
  // The option list knows which names are still resolving; the field passes that on so the
  // checklist keeps drawing a skeleton for them now that it builds its own rows.
  const accountLoading = computed<Set<string>>(
    () => new Set(get(accountOptions).filter(option => option.loading).map(option => option.value)),
  );
  // Computed rather than mapped on each call: `suggest` is read once per field per keystroke while
  // the bar narrows, and this rebuilt the full address list every time.
  const accountValues = computed<string[]>(() => get(accountOptions).map(option => option.value));
  const accountField = toHistoryAccountField(t, {
    resolveCaption,
    resolveKeywords: (value: string): string | undefined => get(accountKeywords).get(value),
    resolveLabel,
    resolveLoading: (value: string): boolean => get(accountLoading).has(value),
    suggest: (): string[] => get(accountValues),
  });
  const ignoredField = toHistoryIgnoredField(t);
  // An action's direction is what its icon colour carries, the same in/out reading the event rows
  // use, so a verb looks the same on a pill as it does in the table.
  const directionColors = { in: 'success', neutral: 'secondary', out: 'error' } as const;
  const actionOptions = computed<ActionFieldOption[]>(() => get(actionRows).map(row => ({
    icon: { color: directionColors[row.direction], icon: row.icon },
    label: row.label,
    verbKey: row.verbKey,
  })));
  const actionField = toHistoryActionField(t, (): ActionFieldOption[] => get(actionOptions));
  const stateField = toHistoryStateField(
    t,
    Object.values(HistoryEventState),
    value => (isValidHistoryEventState(value) ? stateConfigs[value].label : value),
    value => (isValidHistoryEventState(value) ? stateConfigs[value] : undefined),
  );

  return computed<FieldDef[]>(() => {
    const base = toHistoryEventFields({
      ...shared,
      resolveEventSubTypeName: getHistoryEventSubTypeName,
      resolveEventTypeName: getHistoryEventTypeName,
      t,
    }, {
      counterparties: (): string[] => get(counterparties),
      disabled: get(disabled),
      entryTypes: toValue(entryTypes),
      eventSubtypes: (): string[] => subtypesFor(get(selectedEventTypes)),
      eventTypes: (): string[] => get(historyEventTypes),
      locations: (): string[] => get(associatedLocations),
      searchAsset,
      subtypesFor,
    });
    const withParams = [...base, actionField, stateField, ignoredField];
    return toValue(useExternalAccountFilter) ? withParams : [...withParams, accountField];
  });
}
