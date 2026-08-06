<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { DataIssue, DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import type { IssueDescription } from '@/modules/history/data-issues/types';
import { startPromise } from '@shared/utils';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import DataIssueDetailContent from '@/modules/history/data-issues/components/DataIssueDetailContent.vue';
import DataIssuePanelCard from '@/modules/history/data-issues/components/DataIssuePanelCard.vue';
import ResolveManuallyDialog from '@/modules/history/data-issues/components/ResolveManuallyDialog.vue';
import { IssueState, NON_TERMINAL_STATES } from '@/modules/history/data-issues/constants';
import { describeIssue, relatedEventRoute } from '@/modules/history/data-issues/transforms';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';
import { useDataIssueFields } from '@/modules/history/data-issues/use-data-issue-fields';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { DataIssuesFilterValueKeys, type Filters, useDataIssuesFilter } from '@/modules/history/data-issues/use-data-issues-filter';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import PinnedDetailSheet from '@/modules/shell/pinned/PinnedDetailSheet.vue';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

/** Mirrors whether a stacked detail/resolve overlay is open, so the host drawer can stay stateless. */
const subDialogOpen = defineModel<boolean>('subDialogOpen', { default: false });

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const issues = ref<DataIssue[]>([]);
const loading = ref<boolean>(false);

const { fetchData } = useDataIssues();
const { refreshSummary } = useDataIssuesSummary();

// Reuse the full-page filter fields, but expose only the compact subset that fits the preview:
// state, kind, asset and account. Keyed by wire key, which is what a field carries — the period
// pill is left out because the preview is a glance at what needs attention now, not a search.
const PANEL_FILTER_KEYS: readonly string[] = [
  DataIssuesFilterValueKeys.STATE,
  DataIssuesFilterValueKeys.KIND,
  DataIssuesFilterValueKeys.ASSET,
  DataIssuesFilterValueKeys.ACCOUNT,
];
const { matchers } = useDataIssuesFilter();
const fields = useDataIssueFields(matchers);
const panelFields = computed<FieldDef[]>(() =>
  get(fields).filter(field => PANEL_FILTER_KEYS.includes(field.key)));
const pillLabels = usePillBarLabels();
const panelFilters = ref<Filters>({});
const hasPanelFilters = computed<boolean>(() => Object.keys(get(panelFilters)).length > 0);

// The filter's suggestion dropdown is a RuiMenu teleported to <body>, so clicking a
// suggestion (e.g. an asset) reads as a click outside the floating drawer and would
// dismiss it. Keep the drawer stateless while the filter is engaged, and hold that
// state for a short grace period after focus leaves so the trailing click on a
// teleported suggestion (which fires after the input blurs) is still ignored.
const filterWrapper = useTemplateRef<HTMLElement>('filterWrapper');
const { focused: filterFocused } = useFocusWithin(filterWrapper);
const filterEngaged = ref<boolean>(false);
const { start: scheduleDisengage, stop: cancelDisengage } = useTimeoutFn(() => {
  set(filterEngaged, false);
}, 300, { immediate: false });

watch(filterFocused, (focused) => {
  if (focused) {
    cancelDisengage();
    set(filterEngaged, true);
  }
  else {
    scheduleDisengage();
  }
});

// Filter values are typed `string | string[] | boolean`; our matchers only ever
// produce strings/arrays, so narrow to the shapes the request payload accepts.
type FilterValue = string | string[] | boolean | undefined;

function asMulti(value: FilterValue): string | string[] | undefined {
  return value === undefined || typeof value === 'boolean' ? undefined : value;
}

function asSingle(value: FilterValue): string | undefined {
  return typeof value === 'string' ? value : undefined;
}

// The panel is a glanceable inbox preview: it loads one page at a time and appends
// more as the user scrolls, rather than mounting the entire (possibly 100+) list at
// once (each card resolves an asset icon/avatar and runs observers).
const PAGE_SIZE = 25;
const offset = ref<number>(0);
const total = ref<number>(0);
const loadingMore = ref<boolean>(false);
const canLoadMore = computed<boolean>(() => get(issues).length < get(total));

function buildPayload(): DataIssuesRequestPayload {
  const filters = get(panelFilters);
  return {
    asset: asSingle(filters.asset),
    kind: asMulti(filters.kind),
    limit: PAGE_SIZE,
    locationLabel: asSingle(filters.locationLabel),
    offset: get(offset),
    state: asMulti(filters.state) ?? [...NON_TERMINAL_STATES],
  };
}

async function loadList(append: boolean): Promise<void> {
  const busy = append ? loadingMore : loading;
  set(busy, true);
  try {
    const collection = await fetchData(buildPayload());
    set(issues, append ? [...get(issues), ...collection.data] : collection.data);
    set(total, collection.found);
  }
  finally {
    set(busy, false);
  }
}

/** Reloads from the first page, replacing the current list (on mount, filter change, refresh). */
async function refreshList(): Promise<void> {
  set(offset, 0);
  await loadList(false);
}

/** Appends the next page; guarded so overlapping scroll events do not double-fetch. */
async function loadMore(): Promise<void> {
  if (get(loading) || get(loadingMore) || !get(canLoadMore))
    return;
  set(offset, get(offset) + PAGE_SIZE);
  await loadList(true);
}

async function reloadAll(): Promise<void> {
  await Promise.all([refreshList(), refreshSummary()]);
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

interface PanelRow {
  issue: DataIssue;
  description: IssueDescription;
  eventRoute: RouteLocationRaw | undefined;
}

const rows = computed<PanelRow[]>(() => get(issues).map((issue) => {
  const description = describeIssue(issue);
  return {
    description,
    eventRoute: relatedEventRoute(issue.kind, description.eventIdentifier, issue.groupIdentifier, issue.asset),
    issue,
  };
}));

const router = useRouter();
const route = useRoute();
const { clearHighlightTarget } = useHistoryEventNavigation();
const { syncCompleted } = useSyncCompleted();

async function goToEvent(target: RouteLocationRaw): Promise<void> {
  await router.push(target);
}

// The route query is the single source of truth for the highlighted history event,
// so the "source" card mirrors it: the card whose event is currently highlighted is
// shown as active. This stays in sync automatically when the highlight is cleared
// from the events view (the card simply stops matching).
const activeEventIdentifier = computed<number | undefined>(() => {
  const raw = get(route).query.highlightedNegativeBalanceEvent;
  const value = Number(Array.isArray(raw) ? raw[0] : raw);
  return Number.isInteger(value) && value > 0 ? value : undefined;
});

const hasActiveSelection = computed<boolean>(() => get(activeEventIdentifier) !== undefined);

function isActiveRow(row: PanelRow): boolean {
  const identifier = row.description.eventIdentifier;
  return identifier !== undefined && identifier === get(activeEventIdentifier);
}

// Clear the selection: strip the highlight query params (which un-highlights both the
// history row and the source card) and drop the paging target so a later filter change
// does not re-navigate to the stale event. Mirrors clearHighlight() in the movement
// matching pinned panel.
async function clearSelection(): Promise<void> {
  clearHighlightTarget(HighlightTargetTypes.NEGATIVE_BALANCE);
  const { highlightedNegativeBalanceEvent, targetGroupIdentifier, ...remainingQuery } = get(route).query;
  if (highlightedNegativeBalanceEvent || targetGroupIdentifier)
    await router.replace({ query: remainingQuery });
}

// Resolving needs the issue selected first (the resolve dialog reads the selected
// issue), so a card-triggered resolve selects then opens the dialog.
function onResolveFromCard(issue: DataIssue): void {
  set(modelSelectedIssue, issue);
  onResolveRequest();
}

const { pause, resume } = useIntervalFn(reloadAll, 10_000, { immediate: false });

// While the panel is backgrounded under <KeepAlive> its reactivity stays live, so
// gate the poll and the sync-refetch on activation: a hidden inbox must not keep
// hitting the network. Deferred sync refreshes are caught up once it is shown again.
const active = ref<boolean>(true);
const pendingRefresh = ref<boolean>(false);

function syncPolling(): void {
  if (get(active) && get(hasRemediatingRows))
    resume();
  else
    pause();
}

watch(hasRemediatingRows, syncPolling);

// Reload when the history sync finishes so the inbox reflects the freshly detected
// issues (or the all-clear shield) without waiting for the slow poll or a manual refresh.
watch(syncCompleted, () => {
  if (get(active))
    startPromise(reloadAll());
  else
    set(pendingRefresh, true);
});

onActivated(() => {
  set(active, true);
  syncPolling();
  if (get(pendingRefresh)) {
    set(pendingRefresh, false);
    startPromise(reloadAll());
  }
});

onDeactivated(() => {
  set(active, false);
  pause();
});

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
