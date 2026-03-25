<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import DateDisplay from '@/components/display/DateDisplay.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import {
  type InternalTxConflict,
  type InternalTxConflictAction,
  InternalTxConflictActions,
  InternalTxConflictStatuses,
  type RedecodeReason,
  RedecodeReasons,
  type RepullReason,
  RepullReasons,
} from './types';
import { useInternalTxConflictResolution } from './use-internal-tx-conflict-resolution';
import { useInternalTxConflictSelection } from './use-internal-tx-conflict-selection';
import { useInternalTxConflicts } from './use-internal-tx-conflicts';

const { compact = false, highlightedTxHash } = defineProps<{
  compact?: boolean;
  highlightedTxHash?: string;
}>();

const emit = defineEmits<{
  'show-in-events': [conflict: InternalTxConflict];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  conflicts,
  failedCount,
  fetchConflicts,
  fetchCounts,
  filters,
  loading,
  matchers,
  pagination,
  pendingCount,
  setFilter,
  sort,
} = useInternalTxConflicts();

const {
  areAllSelected,
  clearSelection,
  isSelected,
  selectedConflicts,
  selectedCount,
  toggleAllOnPage,
  toggleSelection,
} = useInternalTxConflictSelection();

const {
  cancelResolution,
  isResolving,
  progress,
  resolveMany,
  resolveOne,
} = useInternalTxConflictResolution();

const isRunning = computed<boolean>(() => get(progress).isRunning);

const TAB_STATUSES = [
  InternalTxConflictStatuses.PENDING,
  InternalTxConflictStatuses.FAILED,
  InternalTxConflictStatuses.FIXED,
] as const;

const activeTab = ref<number>(0);

const headers = computed<DataTableColumn<InternalTxConflict>[]>(() => {
  if (compact) {
    return [
      { key: 'selection', label: '', sortable: false },
      { key: 'chain', label: '', sortable: true, cellClass: '!p-1', class: '!p-1' },
      { key: 'txHash', label: t('internal_tx_conflicts.columns.tx_hash'), sortable: true },
      { key: 'action', label: '', sortable: true, cellClass: '!p-1', class: '!p-1' },
      { key: 'timestamp', label: t('internal_tx_conflicts.columns.timestamp'), sortable: true },
      { key: 'actions', label: '' },
    ];
  }

  return [
    { key: 'selection', label: '', sortable: false },
    { key: 'chain', label: '', sortable: true, cellClass: '!p-1', class: '!p-1' },
    { key: 'txHash', label: t('internal_tx_conflicts.columns.tx_hash'), sortable: true },
    { key: 'action', label: '', sortable: true, cellClass: '!p-1', class: '!p-1' },
    { key: 'timestamp', label: t('internal_tx_conflicts.columns.timestamp'), sortable: true },
    { key: 'reason', label: t('internal_tx_conflicts.columns.reason') },
    { key: 'lastRetryTs', label: t('internal_tx_conflicts.columns.last_retry'), sortable: true },
    { key: 'lastError', label: t('internal_tx_conflicts.columns.last_error'), cellClass: 'max-w-56' },
    { key: 'actions', label: '' },
  ];
});

const actionLabels = computed<Record<InternalTxConflictAction, string>>(() => ({
  [InternalTxConflictActions.FIX_REDECODE]: t('internal_tx_conflicts.actions.fix_redecode'),
  [InternalTxConflictActions.REPULL]: t('internal_tx_conflicts.actions.repull'),
}));

const reasonLabels = computed<Record<RepullReason | RedecodeReason, string>>(() => ({
  [RepullReasons.ALL_ZERO_GAS]: t('internal_tx_conflicts.reasons.all_zero_gas'),
  [RepullReasons.OTHER]: t('internal_tx_conflicts.reasons.other'),
  [RedecodeReasons.DUPLICATE_EXACT_ROWS]: t('internal_tx_conflicts.reasons.duplicate_exact_rows'),
  [RedecodeReasons.MIXED_ZERO_GAS]: t('internal_tx_conflicts.reasons.mixed_zero_gas'),
  [RedecodeReasons.MIXED_ZERO_GAS_AND_DUPLICATE]: t('internal_tx_conflicts.reasons.mixed_zero_gas_and_duplicate'),
}));

const allPageSelected = computed<boolean>(() => areAllSelected(get(conflicts)));

function getActionLabel(action: InternalTxConflictAction): string {
  return get(actionLabels)[action];
}

function getReasonLabel(row: InternalTxConflict): string {
  if (row.repullReason)
    return get(reasonLabels)[row.repullReason];

  if (row.redecodeReason)
    return get(reasonLabels)[row.redecodeReason];

  return '—';
}

async function refreshData(): Promise<void> {
  await Promise.all([fetchConflicts(), fetchCounts()]);
}

function onResolveOne(conflict: InternalTxConflict): void {
  startPromise(resolveOne(conflict, { onComplete: refreshData }));
}

function onResolveSelected(): void {
  startPromise(resolveMany(get(selectedConflicts), { onComplete: refreshData }));
}

watch(activeTab, (tab) => {
  clearSelection();
  setFilter(TAB_STATUSES[tab]);
});

onBeforeMount(() => {
  startPromise(Promise.all([fetchCounts(), fetchConflicts()]));
});

defineExpose({
  refreshData,
});
</script>

<template>
  <div class="flex flex-col flex-1 overflow-hidden">
    <RuiTabs
      v-model="activeTab"
      class="border-b border-default"
      color="primary"
    >
      <RuiTab>
        {{ t('internal_tx_conflicts.tabs.pending') }}
        <RuiChip
          v-if="pendingCount > 0"
          color="warning"
          size="sm"
          class="ml-2 !px-0.5 !py-0"
        >
          {{ pendingCount }}
        </RuiChip>
      </RuiTab>
      <RuiTab>
        {{ t('internal_tx_conflicts.tabs.failed') }}
        <RuiChip
          v-if="failedCount > 0"
          color="error"
          size="sm"
          class="ml-2 !px-0.5 !py-0"
        >
          {{ failedCount }}
        </RuiChip>
      </RuiTab>
      <RuiTab>
        {{ t('internal_tx_conflicts.tabs.fixed') }}
      </RuiTab>
    </RuiTabs>

    <div class="flex flex-col md:flex-row md:items-center gap-2 px-4 pt-4 pb-2 shrink-0">
      <div class="flex items-center gap-3">
        <template v-if="isRunning">
          <RuiProgress
            variant="indeterminate"
            color="primary"
            class="flex-1"
          />
          <span class="text-body-2 whitespace-nowrap">
            {{ t('internal_tx_conflicts.resolution.progress', { completed: progress.completed, total: progress.total }) }}
          </span>
          <RuiButton
            variant="outlined"
            color="error"
            size="sm"
            @click="cancelResolution()"
          >
            {{ t('internal_tx_conflicts.resolution.cancel') }}
          </RuiButton>
        </template>
        <template v-else>
          <span class="text-body-2 whitespace-nowrap">
            {{ t('internal_tx_conflicts.selection.selected', { count: selectedCount }) }}
          </span>
          <RuiButton
            color="primary"
            size="sm"
            :disabled="selectedCount === 0"
            @click="onResolveSelected()"
          >
            {{ t('internal_tx_conflicts.resolution.resolve_selected', { count: selectedCount }) }}
          </RuiButton>
          <RuiButton
            variant="outlined"
            size="sm"
            :disabled="selectedCount === 0"
            @click="clearSelection()"
          >
            {{ t('internal_tx_conflicts.selection.clear') }}
          </RuiButton>
        </template>
      </div>

      <TableFilter
        v-model:matches="filters"
        :matchers="matchers"
        :disabled="loading"
        class="flex-1"
      />
    </div>

    <div
      class="flex-1 overflow-auto"
      :class="compact && 'px-1'"
    >
      <RuiDataTable
        v-model:sort.external="sort"
        v-model:pagination.external="pagination"
        :cols="headers"
        :rows="conflicts"
        :loading="loading"
        row-attr="txHash"
        outlined
        dense
        class="table-inside-dialog"
      >
        <template #header.selection>
          <RuiCheckbox
            :model-value="allPageSelected"
            :disabled="isRunning || conflicts.length === 0"
            color="primary"
            hide-details
            class="!mt-0"
            @update:model-value="toggleAllOnPage(conflicts)"
          />
        </template>
        <template #item.selection="{ row }">
          <RuiCheckbox
            :model-value="isSelected(row)"
            :disabled="isRunning"
            color="primary"
            hide-details
            class="!mt-0"
            @update:model-value="toggleSelection(row)"
          />
        </template>
        <template #item.chain="{ row }">
          <LocationIcon
            :item="row.chain"
            icon
            size="24px"
          />
        </template>
        <template #item.txHash="{ row }">
          <HashLink
            :text="row.txHash"
            :location="row.chain"
            type="transaction"
          />
        </template>
        <template #item.action="{ row }">
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiIcon
                :name="row.action === InternalTxConflictActions.REPULL ? 'lu-refresh-cw' : 'lu-wrench'"
                :color="row.action === InternalTxConflictActions.REPULL ? 'primary' : 'warning'"
                size="18"
              />
            </template>
            {{ getActionLabel(row.action) }}
          </RuiTooltip>
        </template>
        <template #item.timestamp="{ row }">
          <div :class="compact && 'text-xs'">
            <DateDisplay
              v-if="row.timestamp"
              :timestamp="row.timestamp"
            />
            <!-- eslint-disable-next-line @intlify/vue-i18n/no-raw-text -->
            <span v-else>—</span>
            <div
              v-if="compact"
              class="text-rui-text-secondary"
            >
              {{ getReasonLabel(row) }}
            </div>
          </div>
        </template>
        <template #item.reason="{ row }">
          {{ getReasonLabel(row) }}
        </template>
        <template #item.lastRetryTs="{ row }">
          <DateDisplay
            v-if="row.lastRetryTs"
            :timestamp="row.lastRetryTs"
          />
          <span v-else>{{ t('internal_tx_conflicts.status.never') }}</span>
        </template>
        <template #item.lastError="{ row }">
          <div
            v-if="row.lastError"
            class="flex items-center gap-1"
          >
            <RuiTooltip
              :popper="{ placement: 'top' }"
              :open-delay="400"
              tooltip-class="max-w-80"
            >
              <template #activator>
                <span class="truncate max-w-48 inline-block align-bottom">
                  {{ row.lastError }}
                </span>
              </template>
              {{ row.lastError }}
            </RuiTooltip>
            <CopyButton
              size="sm"
              :value="row.lastError"
              :tooltip="t('internal_tx_conflicts.actions.copy_error')"
            />
          </div>
          <!-- eslint-disable-next-line @intlify/vue-i18n/no-raw-text -->
          <span v-else>—</span>
        </template>
        <template #item.actions="{ row }">
          <div class="flex items-center">
            <RuiTooltip
              :popper="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiButton
                  variant="text"
                  icon
                  size="sm"
                  :loading="isResolving(row)"
                  :disabled="isRunning || isResolving(row)"
                  @click="onResolveOne(row)"
                >
                  <RuiIcon
                    name="lu-refresh-cw"
                    size="16"
                  />
                </RuiButton>
              </template>
              {{ t('internal_tx_conflicts.resolution.resolve') }}
            </RuiTooltip>
            <RuiTooltip
              :popper="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiButton
                  variant="text"
                  icon
                  size="sm"
                  :disabled="!row.groupIdentifier"
                  :color="highlightedTxHash === row.txHash ? 'warning' : undefined"
                  @click="emit('show-in-events', row)"
                >
                  <RuiIcon
                    :name="highlightedTxHash === row.txHash ? 'lu-eye-off' : 'lu-external-link'"
                    size="16"
                  />
                </RuiButton>
              </template>
              {{ highlightedTxHash === row.txHash
                ? t('internal_tx_conflicts.actions.clear_highlight')
                : t('internal_tx_conflicts.actions.show_in_events')
              }}
            </RuiTooltip>
          </div>
        </template>
      </RuiDataTable>
    </div>
  </div>
</template>
