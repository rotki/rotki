<script lang="ts" setup>
import type { HistoryEventsToggles } from '@/components/history/events/dialog-types';
import type { IgnoreStatus } from '@/modules/history/events/composables/use-history-events-selection-actions';
import type { SelectionState } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import TableStatusFilter from '@/components/helper/TableStatusFilter.vue';
import HistoryEventsExport from '@/components/history/events/HistoryEventsExport.vue';
import HistoryTableActions from '@/components/history/HistoryTableActions.vue';
import LocationLabelSelector from '@/components/history/LocationLabelSelector.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import HistoryRedecodeButton from '@/modules/history/redecode/HistoryRedecodeButton.vue';
import { type MatchedKeywordWithBehaviour, SavedFilterLocation, type SearchMatcher } from '@/types/filtering';
import { useRefPropVModel } from '@/utils/model';

const filters = defineModel<MatchedKeywordWithBehaviour<any>>('filters', { required: true });

const locationLabels = defineModel<string[]>('locationLabels', { required: true });

const toggles = defineModel<HistoryEventsToggles>('toggles', { required: true });

const props = withDefaults(defineProps<{
  matchers: SearchMatcher<any, any>[];
  exportParams: HistoryEventRequestPayload;
  hideAccountSelector?: boolean;
  hideRedecodeButtons?: boolean;
  ignoreStatus?: IgnoreStatus;
  processing?: boolean;
  selection: SelectionState;
}>(), {
  hideAccountSelector: false,
  hideRedecodeButtons: false,
  ignoreStatus: undefined,
  processing: false,
});

const emit = defineEmits<{
  'redecode': [payload: 'all' | 'page' | string[]];
  'selection:action': [action: 'toggle-mode' | 'delete' | 'exit' | 'toggle-all' | 'create-rule' | 'ignore' | 'unignore' | 'toggle-select-all-matching'];
}>();

const { t } = useI18n({ useScope: 'global' });

const customizedEventsOnly = useRefPropVModel(toggles, 'customizedEventsOnly');
const matchExactEvents = useRefPropVModel(toggles, 'matchExactEvents');
const showIgnoredAssets = useRefPropVModel(toggles, 'showIgnoredAssets');
const virtualEventsOnly = useRefPropVModel(toggles, 'virtualEventsOnly');

const hasActiveToggles = logicOr(customizedEventsOnly, showIgnoredAssets, matchExactEvents, virtualEventsOnly);

const canIgnore = computed<boolean>(() => {
  const status = props.ignoreStatus;
  return status ? status.notIgnoredCount > 0 : false;
});

const canUnignore = computed<boolean>(() => {
  const status = props.ignoreStatus;
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
      <RuiBadge
        dot
        :model-value="hasActiveToggles"
        offset-y="10"
        offset-x="-8"
      >
        <TableStatusFilter>
          <div class="py-1 max-w-[16rem]">
            <RuiSwitch
              v-model="customizedEventsOnly"
              color="primary"
              class="p-4"
              hide-details
              :label="t('transactions.filter.customized_only')"
            />
            <RuiDivider />
            <RuiSwitch
              v-model="virtualEventsOnly"
              color="primary"
              class="p-4"
              hide-details
              :label="t('transactions.filter.virtual_only')"
            />
            <RuiDivider />
            <RuiSwitch
              v-model="showIgnoredAssets"
              color="primary"
              class="p-4"
              hide-details
              :label="t('transactions.filter.show_ignored_assets')"
            />
            <RuiDivider />
            <RuiSwitch
              v-model="matchExactEvents"
              color="primary"
              class="p-4"
              :label="t('transactions.filter.match_exact_filter')"
              :hint="t('transactions.filter.match_exact_filter_hint')"
            />
          </div>
        </TableStatusFilter>
      </RuiBadge>
      <TableFilter
        v-model:matches="filters"
        class="min-w-[12rem] md:min-w-[24rem]"
        :matchers="matchers"
        :location="SavedFilterLocation.HISTORY_EVENTS"
      />
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
            @update:model-value="handleToggleAll()"
          />
        </template>
        {{ t('transactions.events.selection_mode.select_all_page') }}
      </RuiTooltip>
      <span
        v-if="!selection.selectAllMatching"
        class="text-sm text-rui-text-secondary -ml-1 mr-2 select-none"
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
            class="!h-10"
            :disabled="!selection.hasAvailableEvents"
            @click="handleToggleMode()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-copy-check"
                size="24"
              />
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

    <LocationLabelSelector
      v-if="!hideAccountSelector"
      v-model="locationLabels"
      class="w-[18rem]"
      hide-details
      dense
      chips
    />
  </HistoryTableActions>
</template>
