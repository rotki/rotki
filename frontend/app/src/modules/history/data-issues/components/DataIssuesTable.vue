<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { SpamAssessment } from '@/modules/assets/spam/use-spam-assessments';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { type DataTableColumn, RuiButton, RuiDataTable, RuiIcon, RuiTooltip, type TablePaginationData } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import SpamAssessmentHint from '@/modules/assets/spam/SpamAssessmentHint.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import DataIssueCardActions from '@/modules/history/data-issues/components/DataIssueCardActions.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import { describeIssue, relatedEventRoute } from '@/modules/history/data-issues/transforms';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const {
  emptyDescription,
  loading = false,
  rows,
  showClearFilters = false,
  spamAssessments,
  spamUnavailable = false,
} = defineProps<{
  rows: DataIssue[];
  loading?: boolean;
  emptyDescription: string;
  showClearFilters?: boolean;
  spamAssessments?: Readonly<Record<string, SpamAssessment>>;
  spamUnavailable?: boolean;
}>();

const emit = defineEmits<{
  'open': [issue: DataIssue];
  'goto': [route: RouteLocationRaw];
  'dismiss': [issue: DataIssue];
  'retry': [issue: DataIssue];
  'resolve': [issue: DataIssue];
  'clear-filters': [];
}>();

defineSlots<{
  /** The filters that narrow the table, shown in the frame above it. */
  toolbar?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const emptyState = useTableEmptyState({ fallback: () => ({ description: emptyDescription }) });

/** Deep-link to the offending history event for a row's quick "go to event" action. */
function eventRouteFor(issue: DataIssue): RouteLocationRaw | undefined {
  return relatedEventRoute(issue.kind, describeIssue(issue).eventIdentifier, issue.groupIdentifier, issue.asset);
}

function isPotentialSpam(asset?: string | null): boolean {
  const assessment = asset ? spamAssessments?.[asset] : undefined;
  return assessment?.status === 'ready' && assessment.prediction.flagged;
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
  <TableFrame>
    <template
      v-if="$slots.toolbar"
      #toolbar
    >
      <slot name="toolbar" />
    </template>
    <div
      v-if="spamUnavailable"
      class="px-4 pt-2 text-caption text-rui-text-secondary"
      data-testid="data-issues-spam-unavailable"
    >
      {{ t('spam_estimate.unavailable_notice') }}
    </div>
    <RuiDataTable
      v-model:pagination.external="pagination"
      dense
      :cols="headers"
      :loading="loading"
      :rows="rows"
      row-attr="id"
      :empty="emptyState"
      data-testid="data-issues-table"
    >
      <template #item.kind="{ row }">
        <DataIssueKindChip :kind="row.kind" />
      </template>
      <template #item.asset="{ row }">
        <div
          v-if="row.asset"
          class="flex flex-wrap items-center gap-1.5"
        >
          <AssetDetails :asset="row.asset" />
          <SpamAssessmentHint
            v-if="isPotentialSpam(row.asset)"
            :assessment="spamAssessments?.[row.asset]"
            standalone
            quiet
          />
        </div>
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
        <TimeAgoDisplay :timestamp="row.createdAt" />
      </template>
      <template #item.actions="{ row }">
        <div class="flex items-center justify-end gap-0.5">
          <DataIssueCardActions
            class="text-rui-text-secondary transition-opacity [tr:not(:hover)_&:not(:focus-within)]:opacity-0 motion-reduce:transition-none"
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
          <span>{{ emptyState.description }}</span>
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
  </TableFrame>
</template>
