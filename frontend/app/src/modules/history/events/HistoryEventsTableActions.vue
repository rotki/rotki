<script lang="ts" setup>
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { DecodeScope } from '@/modules/history/events/event-payloads';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { IgnoreStatus } from '@/modules/history/events/use-history-events-selection-actions';
import type { SelectionState } from '@/modules/history/events/use-selection-mode';
import { type MatchedKeywordWithBehaviour, SavedFilterLocations } from '@/modules/core/table/filtering';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import PillViewsMenu from '@/modules/core/table/pill/PillViewsMenu.vue';
import HistoryEventsExport from '@/modules/history/events/HistoryEventsExport.vue';
import { useHistoryEventsPillBar } from '@/modules/history/events/use-history-events-pill-bar';
import HistoryTableActions from '@/modules/history/HistoryTableActions.vue';
import HistoryRedecodeButton from '@/modules/history/redecode/HistoryRedecodeButton.vue';

const filters = defineModel<MatchedKeywordWithBehaviour<any>>('filters', { required: true });

const locationLabels = defineModel<string[]>('locationLabels', { required: true });

const action = defineModel<string | undefined>('action', { required: true });

const toggles = defineModel<HistoryEventsToggles>('toggles', { required: true });

const { ignoreStatus } = defineProps<{
  fields: FieldDef[];
  exportParams: HistoryEventRequestPayload;
  hideRedecodeButtons?: boolean;
  ignoreStatus?: IgnoreStatus;
  processing?: boolean;
  selection: SelectionState;
}>();

const emit = defineEmits<{
  'redecode': [scope: DecodeScope];
  'selection:action': [action: 'toggle-mode' | 'delete' | 'exit' | 'toggle-all' | 'create-rule' | 'ignore' | 'unignore' | 'toggle-select-all-matching'];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  applyView,
  modelPillParams,
  pillLabels,
  pillState,
  toggleMatchExact,
} = useHistoryEventsPillBar({ action, filters, locationLabels, toggles });

const canIgnore = computed<boolean>(() => {
  const status = ignoreStatus;
  return status ? status.notIgnoredCount > 0 : false;
});

const canUnignore = computed<boolean>(() => {
  const status = ignoreStatus;
  return status ? status.ignoredCount > 0 : false;
});

function handleDelete(): void {
  emit('selection:action', 'delete');
}

function handleCreateRule(): void {
  emit('selection:action', 'create-rule');
}

function handleIgnore(): void {
  emit('selection:action', 'ignore');
}

function handleUnignore(): void {
  emit('selection:action', 'unignore');
}

function handleExit(): void {
  emit('selection:action', 'exit');
}

function handleToggleMode(): void {
  emit('selection:action', 'toggle-mode');
}

function handleToggleAll(): void {
  emit('selection:action', 'toggle-all');
}

function handleToggleSelectAllMatching(): void {
  emit('selection:action', 'toggle-select-all-matching');
}
</script>

<template>
  <HistoryTableActions hide-divider>
    <template #filter>
      <PillFilterBar
        v-model:matches="filters"
        v-model:params="modelPillParams"
        class="flex-1 min-w-[12rem] md:min-w-[24rem]"
        :fields="fields"
        :labels="pillLabels"
      >
        <template #views="{ disabled: barDisabled }">
          <PillViewsMenu
            :fields="fields"
            :location="SavedFilterLocations.HISTORY_EVENTS"
            :state="pillState"
            :disabled="barDisabled"
            @apply="applyView($event)"
          />
        </template>

        <!-- Constrains the active filters to the events themselves rather than their whole
             group, so it only means anything once something is filtered.

             An icon toggle rather than a labelled switch: it sits inside the bar, where the
             pills are what should be read, and its label is long enough to crowd them out. The
             tooltip carries the full name and the explanation the switch's hint used to. -->
        <template #modifiers="{ disabled: barDisabled }">
          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                variant="text"
                size="sm"
                icon
                class="shrink-0"
                :disabled="barDisabled"
                :color="toggles.matchExactEvents ? 'primary' : 'secondary'"
                :class="{ 'bg-rui-primary/10': toggles.matchExactEvents }"
                :aria-pressed="toggles.matchExactEvents"
                data-testid="filter-match-exact"
                @click="toggleMatchExact()"
              >
                <RuiIcon
                  name="lu-focus"
                  size="18"
                />
              </RuiButton>
            </template>
            <div class="max-w-[16rem]">
              <div class="font-medium">
                {{ t('transactions.filter.match_exact_filter') }}
              </div>
              <!-- An icon toggle has no label to read its state from, so the tooltip says which
                   state it is in rather than only what the setting means. -->
              <div class="text-caption">
                {{ toggles.matchExactEvents
                  ? t('transactions.filter.match_exact_filter_enabled')
                  : t('transactions.filter.match_exact_filter_disabled') }}
              </div>
            </div>
          </RuiTooltip>
        </template>
      </PillFilterBar>
    </template>

    <div
      v-if="selection.isActive"
      class="flex items-center gap-1.5 h-10 bg-rui-grey-500/[0.1] rounded-md pl-3 pr-1"
    >
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiCheckbox
            :model-value="selection.isAllSelected || selection.selectAllMatching"
            :indeterminate="selection.isPartiallySelected"
            :disabled="selection.selectAllMatching"
            color="primary"
            hide-details
            size="sm"
            data-testid="selection-select-all-page"
            @update:model-value="handleToggleAll()"
          />
        </template>
        {{ t('transactions.events.selection_mode.select_all_page') }}
      </RuiTooltip>
      <span
        v-if="!selection.selectAllMatching"
        class="text-sm text-rui-text-secondary -ml-1 mr-2 select-none"
        data-testid="selection-count"
      >
        {{ t('transactions.events.selection_mode.selected_count', { count: selection.selectedCount }) }}
      </span>
      <RuiDivider
        v-if="!selection.selectAllMatching"
        vertical
        class="mr-1 -ml-1 h-4"
      />
      <RuiButton
        variant="text"
        :color="selection.selectAllMatching ? 'warning' : 'primary'"
        size="sm"
        class="text-sm hover:underline cursor-pointer mr-2"
        :class="selection.selectAllMatching ? '-ml-3' : '-ml-1'"
        data-testid="selection-select-all-matching"
        @click="handleToggleSelectAllMatching()"
      >
        {{ selection.selectAllMatching ? t('transactions.events.selection_mode.all_matching_selected', { count: selection.totalMatchingCount }) : t('transactions.events.selection_mode.select_all_matching') }}
        <template
          v-if="selection.selectAllMatching"
          #append
        >
          <RuiIcon
            name="lu-x"
            size="18"
          />
        </template>
      </RuiButton>
      <RuiTooltip :open-delay="200">
        <template #activator>
          <RuiButton
            color="error"
            variant="outlined"
            class="h-7 px-2.5"
            :disabled="selection.selectedCount === 0"
            data-testid="selection-delete"
            @click="handleDelete()"
          >
            <RuiIcon
              name="lu-trash-2"
              size="16"
            />
          </RuiButton>
        </template>
        {{ t('transactions.events.selection_mode.delete_selected') }}
      </RuiTooltip>
      <div class="flex">
        <RuiTooltip :open-delay="200">
          <template #activator>
            <RuiButton
              variant="outlined"
              class="h-7 px-2.5 !rounded-r-none"
              :disabled="selection.selectedCount === 0 || !canIgnore || selection.selectAllMatching"
              data-testid="selection-ignore"
              @click="handleIgnore()"
            >
              <RuiIcon
                name="lu-eye-off"
                size="16"
              />
            </RuiButton>
          </template>
          {{ t('transactions.events.selection_mode.ignore') }}
        </RuiTooltip>
        <RuiTooltip :open-delay="200">
          <template #activator>
            <RuiButton
              variant="outlined"
              class="h-7 px-2.5 !rounded-l-none -ml-[1px]"
              :disabled="selection.selectedCount === 0 || !canUnignore || selection.selectAllMatching"
              data-testid="selection-unignore"
              @click="handleUnignore()"
            >
              <RuiIcon
                name="lu-eye"
                size="16"
              />
            </RuiButton>
          </template>
          {{ t('transactions.events.selection_mode.unignore') }}
        </RuiTooltip>
      </div>
      <RuiTooltip :open-delay="200">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            class="h-7 px-2.5"
            :disabled="selection.selectedCount === 0 || selection.selectAllMatching"
            data-testid="selection-create-rule"
            @click="handleCreateRule()"
          >
            <RuiIcon
              name="lu-file-spreadsheet"
              size="16"
            />
          </RuiButton>
        </template>
        {{ t('transactions.events.selection_mode.create_rule') }}
      </RuiTooltip>
      <RuiButton
        variant="text"
        class="h-7 px-2.5"
        data-testid="selection-exit"
        @click="handleExit()"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>
    </div>
    <template v-else>
      <RuiTooltip :open-delay="200">
        <template #activator>
          <RuiButton
            variant="text"
            size="xl"
            :disabled="!selection.hasAvailableEvents"
            data-testid="selection-toggle-mode"
            @click="handleToggleMode()"
          >
            <template #prepend>
              <RuiIcon name="lu-copy-check" />
            </template>
          </RuiButton>
        </template>
        {{ selection.hasAvailableEvents ? t('transactions.events.selection_mode.tooltip') : t('transactions.events.selection_mode.no_events') }}
      </RuiTooltip>

      <HistoryRedecodeButton
        v-if="!hideRedecodeButtons"
        :processing="processing"
        @redecode="emit('redecode', $event)"
      />

      <HistoryEventsExport
        :match-exact-events="toggles.matchExactEvents"
        :filters="exportParams"
      />
    </template>
  </HistoryTableActions>
</template>
