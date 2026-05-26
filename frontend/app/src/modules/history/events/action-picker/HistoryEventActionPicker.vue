<script setup lang="ts">
import type { HistoryEventEntryType } from '@rotki/common';
import HistoryEventActionDirectionBadge from '@/modules/history/events/action-picker/HistoryEventActionDirectionBadge.vue';
import { type EventActionRow, useEventActionPicker } from '@/modules/history/events/action-picker/use-event-action-picker';
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

const { t } = useI18n({ useScope: 'global' });

const { findRowByTypeSubtype, rows } = useEventActionPicker(() => entryType);
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

const FALLBACK_GROUP: Readonly<{ label: string; icon: string }> = {
  icon: 'lu-circle-question-mark',
  label: '',
};

function getGroupConfig(groupId: string): { label: string; icon: string } {
  return get(eventCategoryGroupsData)[groupId] ?? FALLBACK_GROUP;
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

  const row = get(rows).find(r => r.verbKey === verbKey);
  if (!row)
    return;

  const current = get(modelValue);
  if (current && row.combinations.some(c => c.eventType === current.eventType && c.eventSubtype === current.eventSubtype))
    return;

  const first = row.combinations[0];
  if (!first)
    return;

  set(modelValue, { eventSubtype: first.eventSubtype, eventType: first.eventType });
}
</script>

<template>
  <RuiAutoComplete
    :model-value="selectedVerbKey"
    :options="[...rows]"
    key-attr="verbKey"
    text-attr="label"
    variant="outlined"
    :group-by="(row: EventActionRow) => row.groupId"
    :label="triggerLabel"
    :placeholder="t('history_event_action.picker.placeholder')"
    :no-data-text="t('history_event_action.picker.empty')"
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
      <div class="flex items-center gap-2 px-3 py-2 text-xs uppercase tracking-wide text-rui-text-secondary">
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
            {{ item.label }}
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
    <template #footer>
      <div class="px-3 py-1.5 text-[10px] text-rui-text-secondary flex justify-end">
        <span>{{ t('history_event_action.picker.keyboard_hint') }}</span>
      </div>
    </template>
  </RuiAutoComplete>
</template>
