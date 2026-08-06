import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { FieldDef, ValueIcon } from '@/modules/core/table/pill/core/types';
import type { Matcher } from '@/modules/history/data-issues/use-data-issues-filter';
import { type DataIssueFieldResolution, toDataIssueFields } from '@/modules/core/table/filters/data-issue-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { IssueKind, IssueState, KIND_META, STATE_META } from '@/modules/history/data-issues/constants';
import { useDataIssueAccountOptions } from '@/modules/history/data-issues/use-data-issue-account-options';
import { useDataIssuesFormat } from '@/modules/history/data-issues/use-data-issues-format';

/**
 * The chip colours are `RuiChip` colours, which include `grey` — not a context colour, and the one
 * a value with no colour of its own already gets. Everything else maps across unchanged.
 */
function toValueIcon(meta: { color: string; icon: RuiIcons }): ValueIcon {
  switch (meta.color) {
    case 'error':
    case 'info':
    case 'primary':
    case 'secondary':
    case 'success':
    case 'warning':
      return { color: meta.color, icon: meta.icon };
    default:
      return { icon: meta.icon };
  }
}

/**
 * The pill-bar fields for the data issues table. Built inside a computed so the labels track the
 * locale: fields built once at setup keep the language they were created in until the component
 * remounts.
 *
 * State and kind are looked up through maps built from the enums rather than resolved per call: a
 * resolver runs once per candidate value while the bar narrows, so it must not rebuild anything.
 */
export function useDataIssueFields(matchers: MaybeRefOrGetter<Matcher[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Asset, address and date resolution is the same for every table filtering on them, so it comes
  // from one place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const { kindLabel, stateLabel } = useDataIssuesFormat();
  const account = useDataIssueAccountOptions();

  const stateLabels = computed<Map<string, string>>(
    () => new Map(Object.values(IssueState).map(state => [String(state), stateLabel(state)])),
  );
  const kindLabels = computed<Map<string, string>>(
    () => new Map(Object.values(IssueKind).map(kind => [String(kind), kindLabel(kind)])),
  );
  const stateIcons = new Map<string, ValueIcon>(
    Object.entries(STATE_META).map(([state, meta]) => [state, toValueIcon(meta)]),
  );
  const kindIcons = new Map<string, ValueIcon>(
    Object.entries(KIND_META).map(([kind, meta]) => [kind, toValueIcon(meta)]),
  );

  const resolution = computed<DataIssueFieldResolution>(() => ({
    account,
    resolveKindIcon: (value: string): ValueIcon | undefined => kindIcons.get(value),
    resolveKindLabel: (value: string): string => get(kindLabels).get(value) ?? value,
    resolveStateIcon: (value: string): ValueIcon | undefined => stateIcons.get(value),
    resolveStateLabel: (value: string): string => get(stateLabels).get(value) ?? value,
  }));

  return computed<FieldDef[]>(() => toDataIssueFields(toValue(matchers), shared, t, get(resolution)));
}
