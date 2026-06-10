<script setup lang="ts">
import type { HistoryEventEntryType } from '@rotki/common';
import { type HighlightSegment, splitHighlight } from '@/modules/history/events/action-picker/highlight-match';
import HistoryEventActionDirectionBadge from '@/modules/history/events/action-picker/HistoryEventActionDirectionBadge.vue';
import { type EventActionRow, useEventActionPicker } from '@/modules/history/events/action-picker/use-event-action-picker';
import { useRecentActions } from '@/modules/history/events/action-picker/use-recent-actions';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

interface ModelValue {
  eventType: string;
  eventSubtype: string;
}

const modelValue = defineModel<ModelValue | undefined>({ required: true });
const { entryType, disabled = false, label, errorMessages, required = false, hint } = defineProps<{
  entryType?: HistoryEventEntryType;
  disabled?: boolean;
  label?: string;
  errorMessages?: string | string[];
  required?: boolean;
  hint?: string;
}>();
// Synthetic group used to pin frequently picked verbs to the top. Recent rows
// reuse a real row but carry a distinct key/group so RuiAutoComplete doesn't
// collide with the canonical row that also lives in its taxonomy group.
const RECENT_GROUP_ID = '__recent__';
const RECENT_KEY_PREFIX = 'recent:';

const { t } = useI18n({ useScope: 'global' });

const search = ref<string>('');

const { findRowByTypeSubtype, rows } = useEventActionPicker(() => entryType);
const { recent, record } = useRecentActions(() => entryType);
const { eventCategoryGroupsData, getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

const selectedVerbKey = computed<string | undefined>(() => {
  const value = get(modelValue);
  if (!value)
    return undefined;

  return findRowByTypeSubtype(value.eventType, value.eventSubtype)?.verbKey;
});

watch([selectedVerbKey, rows], ([verbKey, currentRows]) => {
  if (!get(modelValue) || verbKey || currentRows.length === 0)
    return;

  set(modelValue, undefined);
});

const triggerLabel = computed<string>(() => label ?? t('history_event_action.picker.label'));

const trimmedSearch = computed<string>(() => get(search).trim());

// Map the persisted recent verb keys back onto live rows (dropping any that the
// current entry type filtered out), tagging them for the synthetic group.
const recentRows = computed<EventActionRow[]>(() => {
  const byKey = new Map(get(rows).map(row => [row.verbKey, row]));
  const result: EventActionRow[] = [];

  for (const verbKey of get(recent)) {
    const row = byKey.get(verbKey);
    if (row)
      result.push({ ...row, groupId: RECENT_GROUP_ID, verbKey: `${RECENT_KEY_PREFIX}${verbKey}` });
  }

  return result;
});

// Recents only make sense while browsing; once a query is typed they'd just
// duplicate the filtered results, so they're dropped.
const displayRows = computed<EventActionRow[]>(() => {
  const base = [...get(rows)];
  if (get(trimmedSearch) || get(recentRows).length === 0)
    return base;

  return [...get(recentRows), ...base];
});

function highlightLabel(value: string): HighlightSegment[] {
  return splitHighlight(value, get(search));
}

const FALLBACK_GROUP: Readonly<{ label: string; icon: string }> = {
  icon: 'lu-circle-question-mark',
  label: '',
};

interface GroupHeaderConfig {
  label: string;
  icon: string;
  classes: string;
  testId?: string;
}

function getGroupConfig(groupId: string): GroupHeaderConfig {
  if (groupId === RECENT_GROUP_ID) {
    return {
      classes: 'text-rui-primary font-medium',
      icon: 'lu-history',
      label: t('history_event_action.picker.recent'),
      testId: 'event-action-picker-recent-header',
    };
  }

  const group = get(eventCategoryGroupsData)[groupId] ?? FALLBACK_GROUP;
  return { classes: 'text-rui-text-secondary', icon: group.icon, label: group.label };
}

function rowEventTypes(row: EventActionRow): string {
  return row.combinations.map(c => `${c.eventType}:${c.eventSubtype}`).join(' ');
}

function subtitleFor(row: EventActionRow): string {
  const first = row.combinations[0];
  if (!first)
    return '';

  const verb = row.label.toLowerCase();
  const typeLabel = getHistoryEventTypeName(first.eventType).trim();
  const subtypeLabel = getHistoryEventSubTypeName(first.eventSubtype).trim();
  const parts: string[] = [];

  if (typeLabel && typeLabel.toLowerCase() !== verb)
    parts.push(typeLabel);

  if (subtypeLabel && subtypeLabel.toLowerCase() !== verb && subtypeLabel.toLowerCase() !== typeLabel.toLowerCase())
    parts.push(subtypeLabel);

  return parts.join(' · ');
}

function onUpdate(verbKey: string | undefined): void {
  // The picker is required and has no clear affordance, so we must reject
  // RuiAutoComplete's implicit clears (Backspace-from-empty, options-watcher
  // resync) and only react to genuine row selections. The defensive watcher
  // above still clears the model when the current value is no longer mappable
  // to a row (e.g. after an entry-type switch).
  if (!verbKey)
    return;

  // A pick from the synthetic recent group carries the prefixed key; resolve it
  // back to the canonical verb before touching the model or the recents store.
  const realKey = verbKey.startsWith(RECENT_KEY_PREFIX) ? verbKey.slice(RECENT_KEY_PREFIX.length) : verbKey;

  const row = get(rows).find(r => r.verbKey === realKey);
  if (!row)
    return;

  const first = row.combinations[0];
  if (!first)
    return;

  // Record even when re-picking the current value so it bubbles back to the top.
  record(realKey);

  const current = get(modelValue);
  if (current && row.combinations.some(c => c.eventType === current.eventType && c.eventSubtype === current.eventSubtype))
    return;

  set(modelValue, { eventSubtype: first.eventSubtype, eventType: first.eventType });
}
</script>

<template>
  <RuiAutoComplete
    v-model:search-input="search"
    :model-value="selectedVerbKey"
    :options="displayRows"
    key-attr="verbKey"
    text-attr="label"
    variant="outlined"
    :group-by="(row: EventActionRow) => row.groupId"
    :label="triggerLabel"
    :placeholder="t('history_event_action.picker.placeholder')"
    :disabled="disabled"
    :required="required"
    :error-messages="errorMessages"
    :hint="hint"
    data-cy="eventActionPicker"
    data-testid="event-action-picker"
    @update:model-value="onUpdate($event)"
  >
    <template #selection="{ item }">
      <div
        class="flex items-center gap-2 min-w-0"
        data-testid="event-action-picker-selection"
      >
        <RuiIcon
          :name="item.icon"
          size="16"
          class="shrink-0 text-rui-text"
        />
        <span class="font-medium text-rui-text truncate">{{ item.label }}</span>
        <HistoryEventActionDirectionBadge
          :direction="item.direction"
          class="shrink-0 ml-2"
        />
      </div>
    </template>
    <template #group-header="{ group }">
      <div
        class="flex items-center gap-2 px-3 py-2 text-xs uppercase tracking-wide"
        :class="getGroupConfig(group).classes"
        :data-testid="getGroupConfig(group).testId"
      >
        <RuiIcon
          :name="getGroupConfig(group).icon"
          size="14"
        />
        <span>{{ getGroupConfig(group).label }}</span>
      </div>
    </template>
    <template #item="{ item }">
      <div
        class="flex items-center gap-3 w-full"
        :data-testid="`event-action-picker-row-${item.verbKey}`"
        :data-event-types="rowEventTypes(item)"
      >
        <RuiIcon
          :name="item.icon"
          size="18"
          class="shrink-0 text-rui-text"
        />
        <div class="flex-1 min-w-0">
          <div class="text-sm text-rui-text truncate">
            <span
              v-for="(segment, index) in highlightLabel(item.label)"
              :key="index"
              :class="{ 'font-bold text-rui-primary': segment.matched }"
            >
              {{ segment.text }}
            </span>
          </div>
          <div
            v-if="subtitleFor(item)"
            class="text-xs text-rui-text-secondary truncate"
          >
            {{ subtitleFor(item) }}
          </div>
        </div>
        <HistoryEventActionDirectionBadge
          :direction="item.direction"
          class="shrink-0"
        />
      </div>
    </template>
    <template #no-data>
      <div
        class="flex flex-col gap-1 px-4 py-3 text-sm text-rui-text-secondary"
        data-testid="event-action-picker-empty"
      >
        <span v-if="trimmedSearch">
          {{ t('history_event_action.picker.empty_state.with_query', { query: trimmedSearch }) }}
        </span>
        <span v-else>
          {{ t('history_event_action.picker.empty_state.no_query') }}
        </span>
        <span class="text-xs">
          {{ t('history_event_action.picker.empty_state.hint') }}
        </span>
      </div>
    </template>
    <template #footer>
      <div class="px-3 py-1.5 text-[10px] text-rui-text-secondary flex justify-end">
        <span>{{ t('history_event_action.picker.keyboard_hint') }}</span>
      </div>
    </template>
  </RuiAutoComplete>
</template>
