import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AssetsWithId } from '@/modules/assets/types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useEventActionPicker } from '@/modules/history/events/action-picker/use-event-action-picker';
import { type ActionFieldOption, toHistoryAccountField, toHistoryActionField, toHistoryEventFields, toHistoryIgnoredField, toHistoryStateField } from '@/modules/history/events/history-event-fields';
import { type HistoryEventsRestrictions, toRestrictionGetters } from '@/modules/history/events/history-events-restrictions';
import { subtypesForTypes } from '@/modules/history/events/mapping/event-type-subtypes';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { isValidHistoryEventState, useHistoryEventStateMapping } from '@/modules/history/events/mapping/use-history-event-state-mapping';
import { HistoryEventState } from '@/modules/history/events/schemas';
import { useAccountFilterOptions } from '@/modules/history/use-account-filter-options';
import { useHistoryStore } from '@/modules/history/use-history-store';

export interface HistoryEventFieldsOptions {
  /**
   * What the view has already decided for the user. The table's own filters take the same bag, so a
   * page states its restrictions once and both read them: a page pinned to one protocol, location,
   * period, validator set or event type has nothing left to offer a pill for.
   */
  restrictions: MaybeRefOrGetter<HistoryEventsRestrictions>;
  /**
   * The table's filter bag, writable: what is picked scopes the asset search and the offered
   * subtypes, and a narrowing prunes the subtypes it stops admitting.
   */
  modelFilters: Ref<Filters>;
}

/**
 * Assembles the pill-bar `FieldDef`s for history events: the fields it sends in its filter bag plus
 * the external param pills — action, state markers, ignored assets and account (`locationLabels`).
 * The account pill is omitted when the view is already pinned to an external account set.
 */
export function useHistoryEventFields(options: HistoryEventFieldsOptions): ComputedRef<FieldDef[]> {
  const { modelFilters: filters } = options;
  const {
    entryTypes,
    eventTypes,
    externalAccounts,
    location: pinnedLocation,
    period,
    protocols,
    validators,
  } = toRestrictionGetters(options.restrictions);

  // What the view fixes, and so the bar does not offer.
  const disabled = computed(() => ({
    eventTypes: eventTypes().length > 0,
    locations: !!pinnedLocation(),
    period: !!period(),
    protocols: protocols().length > 0,
    validators: !!validators(),
  }));

  const { t } = useI18n({ useScope: 'global' });
  const { getHistoryEventSubTypeName, getHistoryEventTypeName, historyEventTypeGlobalMapping, historyEventTypes } = useHistoryEventMappings();
  const { counterparties } = useHistoryEventCounterpartyMappings();
  const { options: accountOptions, resolveCaption, resolveLabel } = useAccountFilterOptions();
  const { associatedLocations } = storeToRefs(useHistoryStore());
  const { assetSearch } = useAssetInfoRetrieval();
  const { stateConfigs } = useHistoryEventStateMapping();
  const { rows: actionRows } = useEventActionPicker();
  const shared = useSharedFieldResolvers();

  /**
   * The field declares this twice over — as the option list it offers, and as what it `admits` —
   * so the narrowing and the pruning of an already-picked subtype cannot disagree.
   */
  const subtypesFor = (eventTypes: readonly string[]): string[] =>
    subtypesForTypes(get(historyEventTypeGlobalMapping), eventTypes);

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

  /**
   * Holds one debounced asset search per scope, rebuilt only when the scoping location changes.
   *
   * @remarks `assetSuggestions` builds the debounce, so calling it inside `searchAsset` instead
   * would give every keystroke a fresh timer that cancels nothing.
   */
  const search = computed(() => assetSuggestions(assetSearch, get(location)));
  const searchAsset = async (value: string): Promise<AssetsWithId> => get(search)(value);

  const accountKeywords = computed<Map<string, string | undefined>>(
    () => new Map(get(accountOptions).map(option => [option.value, option.keywords])),
  );
  const accountLoading = computed<Set<string>>(
    () => new Set(get(accountOptions).filter(option => option.loading).map(option => option.value)),
  );
  const accountValues = computed<string[]>(() => get(accountOptions).map(option => option.value));
  const accountField = toHistoryAccountField(t, {
    resolveCaption,
    resolveKeywords: (value: string): string | undefined => get(accountKeywords).get(value),
    resolveLabel,
    resolveLoading: (value: string): boolean => get(accountLoading).has(value),
    suggest: (): string[] => get(accountValues),
  });
  const ignoredField = toHistoryIgnoredField(t);
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
      entryTypes: entryTypes(),
      eventSubtypes: (): string[] => subtypesFor(get(selectedEventTypes)),
      eventTypes: (): string[] => get(historyEventTypes),
      locations: (): string[] => get(associatedLocations),
      searchAsset,
      subtypesFor,
    });
    const withParams = [...base, actionField, stateField, ignoredField];
    // The view selects accounts itself, so the bar has no account pill to offer.
    return externalAccounts() ? withParams : [...withParams, accountField];
  });
}
