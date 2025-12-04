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
  'selection:action': [action: 'toggle-mode' | 'delete' | 'exit' | 'toggle-all' | 'create-rule' | 'ignore' | 'unignore'];
}>();

const { t } = useI18n({ useScope: 'global' });

const customizedEventsOnly = useRefPropVModel(toggles, 'customizedEventsOnly');
const matchExactEvents = useRefPropVModel(toggles, 'matchExactEvents');
const showIgnoredAssets = useRefPropVModel(toggles, 'showIgnoredAssets');

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
</script>

<template>
  <HistoryTableActions hide-divider>
    <template
      v-if="!selection.isActive"
      #filter
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
      <TableFilter
        v-model:matches="filters"
        class="min-w-[12rem] md:min-w-[24rem]"
        :matchers="matchers"
        :location="SavedFilterLocation.HISTORY_EVENTS"
      />
    </template>

    <template v-if="selection.isActive">
      <RuiCheckbox
        :model-value="selection.isAllSelected"
        :indeterminate="selection.isPartiallySelected"
        color="primary"
        hide-details
        class="ml-2 pt-[1px] h-11"
        @update:model-value="handleToggleAll()"
      />
      <span class="text-sm text-rui-text-secondary mr-4 select-none">
        {{ t('transactions.events.selection_mode.selected_count', { count: selection.selectedCount }) }}
      </span>
      <RuiButton
        color="error"
        variant="outlined"
        class="h-10"
        :disabled="selection.selectedCount === 0"
        @click="handleDelete()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="20"
          />
        </template>
        {{ t('transactions.events.selection_mode.delete_selected') }}
      </RuiButton>
      <div class="flex">
        <RuiButton
          variant="outlined"
          class="h-10 !rounded-r-none"
          :disabled="selection.selectedCount === 0 || !canIgnore"
          @click="handleIgnore()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-eye-off"
              size="20"
            />
          </template>
          {{ t('transactions.events.selection_mode.ignore') }}
        </RuiButton>
        <RuiButton
          variant="outlined"
          class="h-10 !rounded-l-none -ml-[1px]"
          :disabled="selection.selectedCount === 0 || !canUnignore"
          @click="handleUnignore()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-eye"
              size="20"
            />
          </template>
          {{ t('transactions.events.selection_mode.unignore') }}
        </RuiButton>
      </div>
      <RuiButton
        color="primary"
        variant="outlined"
        class="h-10"
        :disabled="selection.selectedCount === 0"
        @click="handleCreateRule()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-settings"
            size="20"
          />
        </template>
        {{ t('transactions.events.selection_mode.create_rule') }}
      </RuiButton>
      <RuiButton
        variant="text"
        class="h-10"
        @click="handleExit()"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>
    </template>
    <template v-else>
      <RuiTooltip>
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

      <LocationLabelSelector
        v-if="!hideAccountSelector"
        v-model="locationLabels"
      />
    </template>
  </HistoryTableActions>
</template>
