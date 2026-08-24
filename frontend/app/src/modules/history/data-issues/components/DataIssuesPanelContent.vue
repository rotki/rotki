<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { Filters } from '@/modules/history/data-issues/use-data-issues-filter';
import { startPromise } from '@shared/utils';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import DataIssueDetailContent from '@/modules/history/data-issues/components/DataIssueDetailContent.vue';
import DataIssuePanelCard from '@/modules/history/data-issues/components/DataIssuePanelCard.vue';
import ResolveManuallyDialog from '@/modules/history/data-issues/components/ResolveManuallyDialog.vue';
import { panelFilterFields } from '@/modules/history/data-issues/data-issues-panel-utils';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';
import { useDataIssueFields } from '@/modules/history/data-issues/use-data-issue-fields';
import { useDataIssuesPanelList } from '@/modules/history/data-issues/use-data-issues-panel-list';
import { useDataIssuesPanelPolling } from '@/modules/history/data-issues/use-data-issues-panel-polling';
import { useDataIssuesPanelSelection } from '@/modules/history/data-issues/use-data-issues-panel-selection';
import { usePanelFilterEngagement } from '@/modules/history/data-issues/use-panel-filter-engagement';
import PinnedDetailSheet from '@/modules/shell/pinned/PinnedDetailSheet.vue';

/** Mirrors whether a stacked detail/resolve overlay is open, so the host drawer can stay stateless. */
const subDialogOpen = defineModel<boolean>('subDialogOpen', { default: false });

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const panelFilters = ref<Filters>({});

const panelFields = panelFilterFields(useDataIssueFields());
const pillLabels = usePillBarLabels();
const hasPanelFilters = computed<boolean>(() => Object.keys(get(panelFilters)).length > 0);

const filterWrapper = useTemplateRef<HTMLElement>('filterWrapper');
const filterEngaged = usePanelFilterEngagement(filterWrapper);

const {
  hasRemediatingRows,
  isEmpty,
  loading,
  loadingMore,
  loadMore,
  refreshList,
  reloadAll,
  rows,
} = useDataIssuesPanelList(panelFilters);

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

const { clearSelection, goToEvent, hasActiveSelection, isActiveRow } = useDataIssuesPanelSelection();

useDataIssuesPanelPolling(hasRemediatingRows, reloadAll);

// Resolving needs the issue selected first (the resolve dialog reads the selected
// issue), so a card-triggered resolve selects then opens the dialog.
function onResolveFromCard(issue: DataIssue): void {
  set(modelSelectedIssue, issue);
  onResolveRequest();
}

watch([modelDrawerOpen, modelResolveOpen, filterEngaged], ([drawer, resolve, filter]) => {
  set(subDialogOpen, drawer || resolve || filter);
});

watchDebounced(panelFilters, () => {
  startPromise(refreshList());
}, { debounce: 300, deep: true });

// Virtualise the loaded cards so only the visible window mounts (each card resolves an
// asset icon/avatar and runs observers), and append the next page as the user nears the
// end. Each card fills its row exactly (the card is `h-full` and distributes its rows
// with flex), so the row height is fixed: 159px card + 8px gap.
const ITEM_HEIGHT = 167;
const { containerProps, list: visibleRows, wrapperProps } = useVirtualList(rows, {
  itemHeight: ITEM_HEIGHT,
  overscan: 4,
});

// Fetch the next page only when the user actually scrolls to the bottom of the loaded
// cards (scroll-based, so it can't loop the way a "last visible index" watcher can).
const { arrivedState } = useScroll(containerProps.ref);
watch(() => arrivedState.bottom, (atBottom) => {
  if (atBottom)
    startPromise(loadMore());
});

onMounted(() => {
  startPromise(reloadAll());
});
</script>

<template>
  <div class="h-full flex-1 min-h-0 overflow-hidden flex flex-col relative">
    <div
      ref="filterWrapper"
      class="px-3 py-2 border-b border-default shrink-0"
    >
      <PillFilterBar
        v-model:matches="panelFilters"
        :fields="panelFields"
        :labels="pillLabels"
      />
    </div>

    <div
      v-if="hasActiveSelection"
      class="flex items-center justify-between gap-2 px-3 py-1.5 border-b border-default bg-rui-primary/5 text-caption"
      data-testid="data-issues-panel-active-selection"
    >
      <span class="text-rui-text-secondary truncate">
        {{ t('data_issues.panel.highlighting_event') }}
      </span>
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        class="shrink-0"
        data-testid="data-issues-panel-clear-selection"
        @click="clearSelection()"
      >
        {{ t('data_issues.panel.clear_selection') }}
      </RuiButton>
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
      v-else-if="isEmpty && hasPanelFilters"
      class="flex flex-col items-center justify-center flex-1 px-6 text-center gap-2 text-rui-text-secondary"
    >
      <RuiIcon
        size="40px"
        name="lu-funnel-x"
      />
      <div class="text-body-2">
        {{ t('data_issues.empty.filtered') }}
      </div>
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
      v-bind="containerProps"
      class="grow px-3 py-2"
      data-testid="data-issues-panel-list"
    >
      <div v-bind="wrapperProps">
        <div
          v-for="{ data: row, index } in visibleRows"
          :key="index"
          :style="{ height: `${ITEM_HEIGHT}px` }"
          class="pb-2"
        >
          <DataIssuePanelCard
            :issue="row.issue"
            :description="row.description"
            :event-route="row.eventRoute"
            :active="isActiveRow(row)"
            @open="openDetail(row.issue)"
            @goto="goToEvent($event)"
            @dismiss="onDismiss($event.id)"
            @retry="onRetry($event.id)"
            @resolve="onResolveFromCard($event)"
          />
        </div>
      </div>
      <div
        v-if="loadingMore"
        class="sticky bottom-0 flex justify-center py-1"
      >
        <RuiProgress
          variant="indeterminate"
          circular
          size="20"
          thickness="2"
          color="primary"
        />
      </div>
    </div>

    <div class="p-3 flex justify-end border-t border-default">
      <RouterLink :to="{ name: '/history/data-issues/' }">
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

    <PinnedDetailSheet
      v-model="modelDrawerOpen"
      :label="t('data_issues.detail.title')"
    >
      <DataIssueDetailContent
        :issue="modelSelectedIssue"
        :busy="modelActionBusy"
        @close="modelDrawerOpen = false"
        @dismiss="onDismiss($event)"
        @retry="onRetry($event)"
        @resolve="onResolveRequest()"
      />
    </PinnedDetailSheet>

    <ResolveManuallyDialog
      v-model="modelResolveOpen"
      :loading="modelActionBusy"
      @confirm="onResolveConfirm($event)"
    />
  </div>
</template>
