import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useEventActionPicker } from '@/modules/history/events/action-picker/use-event-action-picker';
import { type ActionFieldOption, toHistoryAccountField, toHistoryActionField, toHistoryIgnoredField, toHistoryStateField } from '@/modules/history/events/history-event-fields';
import { isValidHistoryEventState, useHistoryEventStateMapping } from '@/modules/history/events/mapping/use-history-event-state-mapping';
import { HistoryEventState } from '@/modules/history/events/schemas';
import { useAccountFilterOptions } from '@/modules/history/use-account-filter-options';

export interface HistoryEventParamFields {
  accountField: FieldDef;
  actionField: FieldDef;
  ignoredField: FieldDef;
  stateField: FieldDef;
}

/**
 * Builds the external param pills of the history events bar: action, state markers, ignored
 * assets and account (`locationLabels`). These are not part of the table's filter bag.
 */
export function useHistoryEventParamFields(): HistoryEventParamFields {
  const { t } = useI18n({ useScope: 'global' });
  const { options: accountOptions, resolveCaption, resolveLabel } = useAccountFilterOptions();
  const { stateConfigs } = useHistoryEventStateMapping();
  const { rows: actionRows } = useEventActionPicker();

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

  return {
    accountField,
    actionField,
    ignoredField,
    stateField,
  };
}
