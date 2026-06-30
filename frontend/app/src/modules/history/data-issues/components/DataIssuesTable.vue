<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import DataIssueCardActions from '@/modules/history/data-issues/components/DataIssueCardActions.vue';
import DataIssueDetectedTime from '@/modules/history/data-issues/components/DataIssueDetectedTime.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import { describeIssue, relatedEventRoute } from '@/modules/history/data-issues/transforms';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

const pagination = defineModel<TablePaginationData>('pagination');

const { emptyDescription, loading = false, rows, showClearFilters = false } = defineProps<{
  rows: DataIssue[];
  loading?: boolean;
  emptyDescription: string;
  showClearFilters?: boolean;
}>();

const emit = defineEmits<{
  'open': [issue: DataIssue];
  'goto': [route: RouteLocationRaw];
  'dismiss': [issue: DataIssue];
  'retry': [issue: DataIssue];
  'resolve': [issue: DataIssue];
  'clear-filters': [];
}>();

const { t } = useI18n({ useScope: 'global' });

/** Deep-link to the offending history event for a row's quick "go to event" action. */
function eventRouteFor(issue: DataIssue): RouteLocationRaw | undefined {
  return relatedEventRoute(issue.kind, describeIssue(issue).eventIdentifier, issue.groupIdentifier, issue.asset);
}

const headers = computed<DataTableColumn<DataIssue>[]>(() => [
  { key: 'kind', label: t('data_issues.headers.kind') },
  { key: 'asset', label: t('common.asset') },
  { key: 'account', label: t('common.account') },
  { key: 'protocol', label: t('data_issues.headers.protocol') },
  { key: 'state', label: t('data_issues.headers.state') },
  { key: 'createdAt', label: t('data_issues.headers.detected') },
  { align: 'end', key: 'actions', label: '' },
]);
</script>

<template>
  <RuiDataTable
    v-model:pagination.external="pagination"
    outlined
    dense
    :cols="headers"
    :loading="loading"
    :rows="rows"
    row-attr="id"
    :empty="{ description: emptyDescription }"
    data-testid="data-issues-table"
    @click:row="emit('open', $event)"
  >
    <template #item.kind="{ row }">
      <DataIssueKindChip :kind="row.kind" />
    </template>
    <template #item.asset="{ row }">
      <AssetDetails
        v-if="row.asset"
        :asset="row.asset"
      />
      <span
        v-else
        class="text-rui-text-secondary"
      >
        -
      </span>
    </template>
    <template #item.account="{ row }">
      <HistoryEventAccount
        v-if="row.locationLabel"
        :location="row.location"
        :location-label="row.locationLabel"
      />
      <LocationDisplay
        v-else
        :identifier="row.location"
      />
    </template>
    <template #item.protocol="{ row }">
      <CounterpartyDisplay
        v-if="row.protocol"
        :counterparty="row.protocol"
      />
      <span
        v-else
        class="text-rui-text-secondary"
      >
        -
      </span>
    </template>
    <template #item.state="{ row }">
      <DataIssueStateChip :state="row.state" />
    </template>
    <template #item.createdAt="{ row }">
      <DataIssueDetectedTime :timestamp="row.createdAt" />
    </template>
    <template #item.actions="{ row }">
      <div class="flex items-center justify-end gap-0.5">
        <DataIssueCardActions
          :issue="row"
          :event-route="eventRouteFor(row)"
          @goto="emit('goto', $event)"
          @dismiss="emit('dismiss', $event)"
          @retry="emit('retry', $event)"
          @resolve="emit('resolve', $event)"
        />
        <RuiTooltip :open-delay="300">
          <template #activator>
            <RuiButton
              variant="text"
              icon
              size="sm"
              :aria-label="t('data_issues.view_details')"
              data-testid="data-issues-view-details"
              @click.stop="emit('open', row)"
            >
              <RuiIcon
                name="lu-chevron-right"
                size="18"
                class="text-rui-text-secondary"
              />
            </RuiButton>
          </template>
          {{ t('data_issues.view_details') }}
        </RuiTooltip>
      </div>
    </template>

    <template
      v-if="showClearFilters"
      #empty-description
    >
      <div class="flex flex-col items-center gap-2 py-2">
        <span>{{ emptyDescription }}</span>
        <RuiButton
          size="sm"
          variant="text"
          color="primary"
          @click="emit('clear-filters')"
        >
          {{ t('data_issues.empty.clear_filters') }}
        </RuiButton>
      </div>
    </template>
  </RuiDataTable>
</template>
