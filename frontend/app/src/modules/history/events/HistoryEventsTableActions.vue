<script lang="ts" setup>
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { IgnoreStatus } from '@/modules/history/events/use-history-events-selection-actions';
import type { SelectionState } from '@/modules/history/events/use-selection-mode';
import { type MatchedKeywordWithBehaviour, SavedFilterLocations } from '@/modules/core/table/filtering';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import PillViewsMenu from '@/modules/core/table/pill/PillViewsMenu.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';
import HistoryEventsExport from '@/modules/history/events/HistoryEventsExport.vue';
import { useHistoryEventsPillBar } from '@/modules/history/events/use-history-events-pill-bar';
import HistoryTableActions from '@/modules/history/HistoryTableActions.vue';

const filters = defineModel<MatchedKeywordWithBehaviour<any>>('filters', { required: true });

const locationLabels = defineModel<string[]>('locationLabels', { required: true });

const action = defineModel<string | undefined>('action', { required: true });

const toggles = defineModel<HistoryEventsToggles>('toggles', { required: true });

const { ignoreStatus } = defineProps<{
  fields: FieldDef[];
  exportParams: HistoryEventRequestPayload;
  ignoreStatus?: IgnoreStatus;
  selection: SelectionState;
}>();

const emit = defineEmits<{
  'selection:action': [action: 'toggle-mode' | 'delete' | 'clear' | 'exit' | 'toggle-all' | 'create-rule' | 'ignore' | 'unignore' | 'toggle-select-all-matching'];
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

function handleClear(): void {
  emit('selection:action', 'clear');
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
    <template
      v-if="!selection.isActive"
      #filter
    >
      <PillFilterBar
        v-model:matches="filters"
        v-model:params="modelPillParams"
        class="flex-1 min-w-48 md:min-w-96 max-sm:order-last max-sm:basis-full"
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
            <div class="max-w-64">
              <div class="font-medium">
                {{ t('transactions.filter.match_exact_filter') }}
              </div>
              <div class="text-caption">
                {{ toggles.matchExactEvents
                  ? t('transactions.filter.match_exact_filter_enabled')
                  : t('transactions.filter.match_exact_filter_disabled') }}
              </div>
            </div>
          </RuiTooltip>
        </template>
      </PillFilterBar>

      <HistoryEventsExport
        class="max-sm:ml-auto"
        :match-exact-events="toggles.matchExactEvents"
        :filters="exportParams"
      />
    </template>

    <TableSelectionBar
      v-if="selection.isActive"
      class="grow"
      :count="selection.selectedCount"
      exitable
      @clear="handleClear()"
      @exit="handleExit()"
    >
      <template #select-all>
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
      </template>

      <template #scope>
        <RuiButton
          variant="text"
          size="sm"
          :color="selection.selectAllMatching ? 'warning' : 'primary'"
          data-testid="selection-select-all-matching"
          @click="handleToggleSelectAllMatching()"
        >
          {{ selection.selectAllMatching
            ? t('transactions.events.selection_mode.all_matching_selected', { count: selection.totalMatchingCount })
            : t('transactions.events.selection_mode.select_all_matching') }}
          <template
            v-if="selection.selectAllMatching"
            #append
          >
            <RuiIcon
              name="lu-x"
              size="16"
            />
          </template>
        </RuiButton>
      </template>

      <RuiButton
        size="sm"
        variant="outlined"
        color="error"
        :disabled="selection.selectedCount === 0"
        :title="t('transactions.events.selection_mode.delete_selected')"
        data-testid="selection-delete"
        @click="handleDelete()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="16"
          />
        </template>
        {{ t('common.actions.delete') }}
      </RuiButton>
      <RuiButton
        size="sm"
        variant="outlined"
        :disabled="selection.selectedCount === 0 || !canIgnore || selection.selectAllMatching"
        :title="t('transactions.events.selection_mode.ignore')"
        data-testid="selection-ignore"
        @click="handleIgnore()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-eye-off"
            size="16"
          />
        </template>
        {{ t('ignore_buttons.ignore') }}
      </RuiButton>
      <RuiButton
        size="sm"
        variant="outlined"
        :disabled="selection.selectedCount === 0 || !canUnignore || selection.selectAllMatching"
        :title="t('transactions.events.selection_mode.unignore')"
        data-testid="selection-unignore"
        @click="handleUnignore()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-eye"
            size="16"
          />
        </template>
        {{ t('ignore_buttons.unignore') }}
      </RuiButton>
      <RuiButton
        size="sm"
        variant="outlined"
        :disabled="selection.selectedCount === 0 || selection.selectAllMatching"
        :title="t('transactions.events.selection_mode.create_rule')"
        data-testid="selection-create-rule"
        @click="handleCreateRule()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-file-spreadsheet"
            size="16"
          />
        </template>
        {{ t('transactions.events.selection_mode.accounting_rule') }}
      </RuiButton>
    </TableSelectionBar>
    <template v-else>
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            :disabled="!selection.hasAvailableEvents"
            data-testid="selection-toggle-mode"
            @click="handleToggleMode()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-copy-check"
                size="18"
              />
            </template>
            {{ t('common.actions.select') }}
          </RuiButton>
        </template>
        {{ selection.hasAvailableEvents ? t('transactions.events.selection_mode.tooltip') : t('transactions.events.selection_mode.no_events') }}
      </RuiTooltip>
    </template>
  </HistoryTableActions>
</template>
