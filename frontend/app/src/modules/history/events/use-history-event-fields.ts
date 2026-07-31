import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Matcher } from '@/modules/core/table/filters/use-events-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { type ActionFieldOption, toHistoryAccountField, toHistoryActionField, toHistoryEventFields, toHistoryIgnoredField, toHistoryStateField } from '@/modules/core/table/filters/history-event-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useEventActionPicker } from '@/modules/history/events/action-picker/use-event-action-picker';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { isValidHistoryEventState, useHistoryEventStateMapping } from '@/modules/history/events/mapping/use-history-event-state-mapping';
import { HistoryEventState } from '@/modules/history/events/schemas';
import { useAccountFilterOptions } from '@/modules/history/use-account-filter-options';

/**
 * Assembles the pill-bar `FieldDef`s for history events: the matcher-backed fields (with location
 * ids mapped to display names) plus the external param pills, state markers and account
 * (`locationLabels`). The account pill is omitted when the view is already pinned to an external
 * account set.
 */
export function useHistoryEventFields(
  matchers: MaybeRefOrGetter<Matcher[]>,
  useExternalAccountFilter: MaybeRefOrGetter<boolean | undefined>,
): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  const { getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();
  const { options: accountOptions, resolveCaption, resolveLabel } = useAccountFilterOptions();
  const { stateConfigs } = useHistoryEventStateMapping();
  // The bar offers the same verbs the event form's action picker does, from the same model, so a
  // filter and an edit speak of events in one vocabulary.
  const { rows: actionRows } = useEventActionPicker();
  // Asset, location, protocol, address and date resolution is the same for every table that
  // filters on them, so it comes from one place rather than being restated here.
  const shared = useSharedFieldResolvers();

  // The option list already carries `address name tags` per account for its own search box; the
  // bar reuses it so an account is findable by any of them from the inline input too.
  const accountKeywords = computed<Map<string, string | undefined>>(
    () => new Map(get(accountOptions).map(option => [option.value, option.keywords])),
  );
  // Computed rather than mapped on each call: `suggest` is read once per field per keystroke while
  // the bar narrows, and this rebuilt the full address list every time.
  const accountValues = computed<string[]>(() => get(accountOptions).map(option => option.value));
  const accountField = toHistoryAccountField(t, {
    resolveCaption,
    resolveKeywords: (value: string): string | undefined => get(accountKeywords).get(value),
    resolveLabel,
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
    const base = toHistoryEventFields(toValue(matchers), {
      ...shared,
      resolveEventSubTypeName: getHistoryEventSubTypeName,
      resolveEventTypeName: getHistoryEventTypeName,
      t,
    });
    const withParams = [...base, actionField, stateField, ignoredField];
    return toValue(useExternalAccountFilter) ? withParams : [...withParams, accountField];
  });
}
