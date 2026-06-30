<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { startPromise } from '@shared/utils';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import DataIssueDetailDrawer from '@/modules/history/data-issues/components/DataIssueDetailDrawer.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import ResolveManuallyDialog from '@/modules/history/data-issues/components/ResolveManuallyDialog.vue';
import { IssueState, NON_TERMINAL_STATES } from '@/modules/history/data-issues/constants';
import { describeIssue } from '@/modules/history/data-issues/transforms';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import { Routes } from '@/router/routes';

/** Mirrors whether a stacked detail/resolve overlay is open, so the host drawer can stay stateless. */
const subDialogOpen = defineModel<boolean>('subDialogOpen', { default: false });

const { pinned = false } = defineProps<{
  pinned?: boolean;
}>();

const emit = defineEmits<{
  'close': [];
  'toggle-pin': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { isLgAndDown } = useBreakpoint();

const issues = ref<DataIssue[]>([]);
const loading = ref<boolean>(false);

const { fetchData } = useDataIssues();
const { refreshSummary } = useDataIssuesSummary();

async function loadList(): Promise<void> {
  set(loading, true);
  try {
    const collection = await fetchData({ limit: 100, offset: 0, state: [...NON_TERMINAL_STATES] });
    set(issues, collection.data);
  }
  finally {
    set(loading, false);
  }
}

async function reloadAll(): Promise<void> {
  await Promise.all([loadList(), refreshSummary()]);
}

const {
  modelActionBusy,
  modelDrawerOpen,
  modelResolveOpen,
  modelSelectedIssue,
  onDismiss,
  onResolveConfirm,
  onResolveRequest,
  onRetry,
  openDetail,
} = useDataIssueDetailActions(reloadAll);

const isEmpty = computed<boolean>(() => get(issues).length === 0);

const hasRemediatingRows = computed<boolean>(() =>
  get(issues).some(issue => issue.state === IssueState.AUTO_REMEDIATING));

function summaryOf(issue: DataIssue): string {
  return describeIssue(issue, (key, params) => t(key, params ?? {})).summary;
}

const { pause, resume } = useIntervalFn(reloadAll, 10_000, { immediate: false });

watch(hasRemediatingRows, (remediating) => {
  if (remediating)
    resume();
  else
    pause();
});

watch([modelDrawerOpen, modelResolveOpen], ([drawer, resolve]) => {
  set(subDialogOpen, drawer || resolve);
});

onMounted(() => {
  startPromise(reloadAll());
});
</script>

<template>
  <div class="h-full flex-1 min-h-0 overflow-hidden flex flex-col">
    <div class="flex justify-between items-center p-2 pl-4 border-b border-default">
      <div class="text-h6">
        {{ t('data_issues.panel.title') }}
      </div>
      <div class="flex items-center">
        <RuiTooltip
          v-if="!isLgAndDown"
          :open-delay="300"
        >
          <template #activator>
            <RuiButton
              variant="text"
              icon
              size="sm"
              :active="pinned"
              data-testid="data-issues-panel-pin"
              @click="emit('toggle-pin')"
            >
              <RuiIcon :name="pinned ? 'lu-pin-off' : 'lu-pin'" />
            </RuiButton>
          </template>
          {{ pinned ? t('data_issues.panel.unpin') : t('data_issues.panel.pin') }}
        </RuiTooltip>
        <RuiButton
          variant="text"
          icon
          size="sm"
          @click="emit('close')"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </div>
    </div>

    <div
      v-if="loading && isEmpty"
      class="flex flex-1 items-center justify-center"
    >
      <RuiProgress
        variant="indeterminate"
        circular
        size="32"
        thickness="2"
        color="primary"
      />
    </div>

    <div
      v-else-if="isEmpty"
      class="flex flex-col items-center justify-center flex-1 px-6 text-center gap-2"
    >
      <RuiIcon
        size="64px"
        color="success"
        name="lu-shield-check"
      />
      <div class="text-rui-text text-lg mt-2">
        {{ t('data_issues.empty.all_clear_title') }}
      </div>
      <div class="text-rui-text-secondary text-body-2">
        {{ t('data_issues.empty.all_clear_subtitle') }}
      </div>
    </div>

    <div
      v-else
      class="flex flex-col gap-2 px-3 py-2 overflow-y-auto grow"
      data-testid="data-issues-panel-list"
    >
      <RuiCard
        v-for="issue in issues"
        :key="issue.id"
        class="cursor-pointer hover:bg-rui-grey-50 dark:hover:bg-rui-grey-900"
        no-padding
        data-testid="data-issues-panel-item"
        @click="openDetail(issue)"
      >
        <div class="flex flex-col gap-2 p-3">
          <div class="flex items-center justify-between gap-2 flex-wrap">
            <DataIssueKindChip :kind="issue.kind" />
            <DataIssueStateChip :state="issue.state" />
          </div>
          <p class="text-body-2 text-rui-text-secondary line-clamp-2">
            {{ summaryOf(issue) }}
          </p>
          <div class="flex items-center justify-between gap-2 text-caption text-rui-text-secondary">
            <AssetDetails
              v-if="issue.asset"
              :asset="issue.asset"
              size="20px"
            />
            <LocationDisplay
              v-else-if="issue.locationLabel"
              :identifier="issue.locationLabel"
              :opens-details="false"
            />
            <LocationDisplay
              v-else
              :identifier="issue.location"
            />
            <DateDisplay :timestamp="issue.createdAt" />
          </div>
        </div>
      </RuiCard>
    </div>

    <div class="p-3 flex justify-end border-t border-default">
      <RouterLink :to="Routes.HISTORY_DATA_ISSUES">
        <RuiButton
          variant="text"
          color="primary"
          data-testid="data-issues-panel-view-all"
          @click="emit('close')"
        >
          <template #append>
            <RuiIcon
              name="lu-arrow-right"
              size="18"
            />
          </template>
          {{ t('data_issues.panel.view_all') }}
        </RuiButton>
      </RouterLink>
    </div>

    <DataIssueDetailDrawer
      v-model="modelDrawerOpen"
      :issue="modelSelectedIssue"
      :busy="modelActionBusy"
      @dismiss="onDismiss($event)"
      @retry="onRetry($event)"
      @resolve="onResolveRequest()"
    />

    <ResolveManuallyDialog
      v-model="modelResolveOpen"
      :loading="modelActionBusy"
      @confirm="onResolveConfirm($event)"
    />
  </div>
</template>
