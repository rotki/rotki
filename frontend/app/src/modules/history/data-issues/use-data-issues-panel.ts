import type { RouteLocationRaw } from 'vue-router';
import type { RequestFailure } from '@/modules/core/api/request-result';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/history/data-issues/data-issue-filter-keys';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { DataIssueError } from '@/modules/history/data-issues/types';
import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { startPromise } from '@shared/utils';
import { useScroll, useVirtualList, type UseVirtualListReturn } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, watch } from 'vue';
import { panelFilterFields } from '@/modules/history/data-issues/data-issues-panel-utils';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';
import { useDataIssueFields } from '@/modules/history/data-issues/use-data-issue-fields';
import { type RemediationRequest, useDataIssueRemediationActions } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import { type PanelRow, useDataIssuesPanelList } from '@/modules/history/data-issues/use-data-issues-panel-list';
import { useDataIssuesPanelPolling } from '@/modules/history/data-issues/use-data-issues-panel-polling';
import { useDataIssuesPanelSelection } from '@/modules/history/data-issues/use-data-issues-panel-selection';

/** Fixed, because the card is `h-full` and distributes its own rows with flex. */
const CARD_HEIGHT = 159;

/** The `pb-2` on each row wrapper in the panel; the two only agree if they are changed together. */
const ROW_GAP = 8;

/** The height of one virtual list row: a card plus the gap below it. */
export const ITEM_HEIGHT = CARD_HEIGHT + ROW_GAP;

interface UseDataIssuesPanelReturn {
  /** The last load's failure, cleared when the next load starts. */
  error: Readonly<Ref<RequestFailure | undefined>>;
  isEmpty: ComputedRef<boolean>;
  loading: Readonly<Ref<boolean>>;
  loadingMore: Readonly<Ref<boolean>>;
  panelFields: FieldDef[];
  refreshList: () => Promise<void>;
  reloadAll: () => Promise<void>;
  /** Why the last dismiss, retry, or remediation failed, on whichever issue. */
  combinedActionFailure: ComputedRef<NamedFailure | undefined>;
  detailBusy: ComputedRef<boolean>;
  detailFailure: ComputedRef<NamedFailure | undefined>;
  modelActionBusy: Ref<boolean>;
  modelDrawerOpen: Ref<boolean>;
  modelEventForm: Ref<GroupEventData | StandaloneEventData | undefined>;
  modelMatchingOpen: Ref<boolean>;
  modelPriceUpdate: Ref<EventPriceUpdatePayload | undefined>;
  modelResolveOpen: Ref<boolean>;
  modelSelectedIssue: Ref<DataIssue | undefined>;
  modelSubModalOpen: Ref<boolean>;
  onDismiss: (id: number) => Promise<void>;
  onModalSaved: () => Promise<void>;
  onReopen: (id: number) => Promise<void>;
  onResolveConfirm: (note: string | undefined) => Promise<void>;
  onResolveRequest: () => void;
  onRetry: (id: number) => Promise<void>;
  openDetail: (issue: DataIssue) => void;
  remediationModalOpen: ComputedRef<boolean>;
  /** Why the last manual resolve failed, for the resolve dialog. */
  resolveFailure: Readonly<Ref<DataIssueError | undefined>>;
  runRemediation: (request: RemediationRequest) => Promise<void>;
  clearSelection: () => Promise<void>;
  goToEvent: (target: RouteLocationRaw) => Promise<void>;
  hasActiveSelection: ComputedRef<boolean>;
  isActiveRow: (row: PanelRow) => boolean;
  onResolveFromCard: (issue: DataIssue) => void;
  /** Bound on the scrolling container, exactly as `useVirtualList` returns it. */
  containerProps: UseVirtualListReturn<PanelRow>['containerProps'];
  /** The rows inside the visible window, with their index in the full list. */
  visibleRows: UseVirtualListReturn<PanelRow>['list'];
  wrapperProps: UseVirtualListReturn<PanelRow>['wrapperProps'];
}

/**
 * The inbox panel's list, its per-issue actions, the event highlight and the polling, rendered
 * through a virtual list that loads the next page at the bottom.
 *
 * @param panelFilters - the pill filters the list is read with
 */
export function useDataIssuesPanel(panelFilters: MaybeRefOrGetter<Filters>): UseDataIssuesPanelReturn {
  const panelFields = panelFilterFields(useDataIssueFields());

  const {
    error,
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
    actionFailure,
    modelActionBusy,
    modelDrawerOpen,
    modelResolveOpen,
    modelSelectedIssue,
    onDismiss,
    onReopen,
    onResolveConfirm,
    onResolveRequest,
    onRetry,
    openDetail,
    resolveFailure,
    selectedIssueFailure,
  } = useDataIssueDetailActions(
    reloadAll,
    () => get(rows).map(({ issue }) => issue),
  );

  const {
    actionFailure: remediationFailure,
    busy: remediationBusy,
    hasModalOpen: remediationModalOpen,
    modelEventForm,
    modelMatchingOpen,
    modelPriceUpdate,
    modelSubModalOpen,
    onModalSaved,
    runRemediation,
  } = useDataIssueRemediationActions(reloadAll);

  const combinedActionFailure = computed(() => get(remediationFailure) ?? get(actionFailure));
  const detailFailure = computed(() => get(remediationFailure) ?? get(selectedIssueFailure));
  const detailBusy = computed<boolean>(() => get(modelActionBusy) || get(remediationBusy));

  const { clearSelection, goToEvent, hasActiveSelection, isActiveRow } = useDataIssuesPanelSelection();

  useDataIssuesPanelPolling(hasRemediatingRows, reloadAll);

  /**
   * Opens the resolve dialog on the issue whose card was acted on.
   *
   * @remarks
   * The two steps are ordered, not incidental. The dialog reads the selected-issue model rather
   * than taking an argument, so the selection has to be in place before the request; the other way
   * round opens it on whatever was selected before, or on nothing at all.
   */
  function onResolveFromCard(issue: DataIssue): void {
    set(modelSelectedIssue, issue);
    onResolveRequest();
  }

  // Only the visible window mounts: every card resolves an asset icon and runs its own observers.
  const { containerProps, list: visibleRows, wrapperProps } = useVirtualList(rows, {
    itemHeight: ITEM_HEIGHT,
    overscan: 4,
  });

  /**
   * Loads the next page once the user reaches the bottom of the cards already rendered.
   *
   * @remarks
   * Driven by scroll position rather than by the last visible index, which can loop: rendering the
   * new page moves that index, which requests another page.
   */
  function loadMoreAtBottom(atBottom: boolean): void {
    if (atBottom)
      startPromise(loadMore());
  }

  const { arrivedState } = useScroll(containerProps.ref);
  watch(() => arrivedState.bottom, loadMoreAtBottom);

  return {
    clearSelection,
    combinedActionFailure,
    containerProps,
    detailBusy,
    detailFailure,
    error,
    goToEvent,
    hasActiveSelection,
    isActiveRow,
    isEmpty,
    loading,
    loadingMore,
    modelActionBusy,
    modelDrawerOpen,
    modelEventForm,
    modelMatchingOpen,
    modelPriceUpdate,
    modelResolveOpen,
    modelSelectedIssue,
    modelSubModalOpen,
    onDismiss,
    onModalSaved,
    onReopen,
    onResolveConfirm,
    onResolveFromCard,
    onResolveRequest,
    onRetry,
    openDetail,
    panelFields,
    refreshList,
    reloadAll,
    remediationModalOpen,
    resolveFailure,
    runRemediation,
    visibleRows,
    wrapperProps,
  };
}
