import type { TablePaginationData } from '@rotki/ui-library';
import type { UseVirtualListReturn } from '@vueuse/core';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { DuplicateHandlingStatus, HighlightType } from '@/modules/history/events/action-types';
import type { PullEventPayload } from '@/modules/history/events/event-payloads';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import type { HistoryEventsRowContext } from '@/modules/history/events/use-history-events-row-context';
import { useHistoryEventsData } from '@/modules/history/events/use-history-events-data';
import { useHistoryEventsForms } from '@/modules/history/events/use-history-events-forms';
import { useHistoryEventsOperations } from '@/modules/history/events/use-history-events-operations';
import { useVirtualRows, type VirtualRow } from '@/modules/history/events/use-virtual-rows';
import { useVirtualScrollHighlight } from '@/modules/history/events/use-virtual-scroll-highlight';

export interface UseHistoryEventsTableOptions {
  /** Paginated group collection owned by the caller's pagination filter. */
  groups: MaybeRefOrGetter<Collection<HistoryEventRow>>;
  /** Current filter payload, reused as the base of the per-group event fetch. */
  requestPayload: MaybeRefOrGetter<HistoryEventRequestPayload | undefined>;
  /** When true, events whose asset is ignored are hidden unless revealed per group. */
  excludeIgnored: MaybeRefOrGetter<boolean>;
  /** Whether the caller is fetching groups; turning true cancels the in-flight event fetch. */
  groupLoading: MaybeRefOrGetter<boolean>;
  /** Restricts the event fetch to these identifiers; undefined loads the whole page. */
  identifiers: MaybeRefOrGetter<string[] | undefined>;
  /** Hides every row action, for embeddings that render events read-only. */
  hideActions: MaybeRefOrGetter<boolean | undefined>;
  /** Duplicate-handling state a group header shows, when the view is triaging duplicates. */
  duplicateHandlingStatus: MaybeRefOrGetter<DuplicateHandlingStatus | undefined>;
  /** Group to highlight as a whole; the auto-scroll falls back to it when no identifiers are given. */
  highlightedGroupIdentifier: MaybeRefOrGetter<string | undefined>;
  /** Individual event identifiers to highlight and scroll to. */
  highlightedIdentifiers: MaybeRefOrGetter<string[] | undefined>;
  /** Highlight style per target, keyed by event identifier or by `group:<groupIdentifier>`. */
  highlightTypes: MaybeRefOrGetter<Record<string, HighlightType> | undefined>;
  /** Table pagination state; a page change resets the scroll unless a highlight scroll is pending. */
  pagination: Ref<TablePaginationData>;
}

export interface UseHistoryEventsTableReturn {
  /** State the table shell renders itself: header, upgrade row, loading and empty states. */
  shell: {
    loading: Readonly<Ref<boolean>>;
    groups: ComputedRef<HistoryEventEntry[]>;
    total: ComputedRef<number>;
    found: ComputedRef<number>;
    entriesFoundTotal: ComputedRef<number | undefined>;
    showUpgradeRow: ComputedRef<boolean>;
  };
  /** Bindings for the virtual scroll container and the rows currently in view. */
  virtual: {
    containerProps: UseVirtualListReturn<VirtualRow>['containerProps'];
    wrapperProps: UseVirtualListReturn<VirtualRow>['wrapperProps'];
    list: UseVirtualListReturn<VirtualRow>['list'];
  };
  /** Redecode confirmation dialog, owned by the table shell rather than by a row. */
  redecode: {
    modelShow: Ref<boolean>;
    payload: Readonly<Ref<PullEventPayload | undefined>>;
    hasCustomEvents: Readonly<Ref<boolean>>;
    showIndexerOptions: Readonly<Ref<boolean>>;
    confirm: (event: { payload: PullEventPayload; deleteCustom: boolean; customIndexersOrder?: string[] }) => void;
  };
  /** To be handed to `provideHistoryEventsRowContext` by the table component. */
  rowContext: HistoryEventsRowContext;
}

/**
 * Composes the five composables the virtual table runs on: the per-group event fetch, the flattened
 * virtual rows, the scroll and highlight bindings, the event operations and the form dialogs.
 *
 * They are wired in a fixed order (each feeds the next), which is why they are assembled here
 * rather than in the component: the component keeps only what its own template renders, and
 * everything the rows need is bundled into `rowContext` for provide/inject.
 */
export function useHistoryEventsTable(
  options: UseHistoryEventsTableOptions,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsTableReturn {
  const {
    duplicateHandlingStatus,
    excludeIgnored,
    groupLoading,
    groups: groupCollection,
    hideActions,
    highlightedGroupIdentifier,
    highlightedIdentifiers,
    highlightTypes,
    identifiers,
    pagination,
    requestPayload,
  } = options;

  const data = useHistoryEventsData({
    excludeIgnored,
    groupLoading,
    groups: groupCollection,
    identifiers,
    requestPayload,
  }, emit);

  const rows = useVirtualRows(data.groups, data.displayedEventsMapped, data.isSubgroupIncomplete);

  const scroll = useVirtualScrollHighlight({
    flattenedRows: rows.flattenedRows,
    getCardHeight: rows.getCardHeight,
    getRowHeight: rows.getRowHeight,
    highlightedGroupIdentifier,
    highlightedIdentifiers,
    highlightTypes,
    loading: data.loading,
    pagination,
  });

  const operations = useHistoryEventsOperations({
    completeEventsMapped: data.completeEventsMapped,
    flattenedEvents: data.events,
  }, emit);

  const forms = useHistoryEventsForms(operations.suggestNextSequenceId, emit);

  /** Lookup map for O(1) group access from a row's group id. */
  const groupsMap = computed<Map<string, HistoryEventEntry>>(() =>
    new Map(get(data.groups).map(group => [group.groupIdentifier, group])),
  );

  const variant = computed<'row' | 'card'>(() => get(scroll.isCardLayout) ? 'card' : 'row');

  function findGroup(groupId: string): HistoryEventEntry | undefined {
    return get(groupsMap).get(groupId);
  }

  function ignoredAssetsState(groupId: string): 'hidden' | 'showing' | undefined {
    if (get(data.groupsShowingIgnoredAssets).has(groupId))
      return 'showing';

    return get(data.groupsWithHiddenIgnoredAssets).has(groupId) ? 'hidden' : undefined;
  }

  const rowContext: HistoryEventsRowContext = {
    actions: {
      addEvent: forms.addEvent,
      addMissingRule: (payload, groupId): void => {
        const group = findGroup(groupId);
        if (group)
          forms.addMissingRule(payload, group);
      },
      deleteEvents: operations.confirmDelete,
      deleteTransaction: operations.confirmTxAndEventsDelete,
      editEvent: (payload, groupId): void => {
        const group = findGroup(groupId);
        if (group)
          forms.editEvent(payload, group);
      },
      loadMore: rows.loadMoreEvents,
      redecode: operations.redecode,
      redecodeWithOptions: operations.redecodeWithOptions,
      refresh: (): void => {
        emit('refresh');
      },
      toggleIgnore: operations.toggle,
      toggleMovementExpanded: rows.toggleMovementExpanded,
      toggleShowIgnoredAssets: data.toggleShowIgnoredAssets,
      toggleSwapExpanded: rows.toggleSwapExpanded,
      unlinkEvent: operations.confirmUnlink,
      unlinkGroup: operations.unlinkGroup,
    },
    display: {
      duplicateHandlingStatus: computed<DuplicateHandlingStatus | undefined>(() => toValue(duplicateHandlingStatus)),
      eventsLoading: data.eventsLoading,
      hideActions: computed<boolean>(() => toValue(hideActions) ?? false),
      variant,
    },
    highlight: {
      getHighlightType: scroll.getHighlightType,
      getSwapHighlightType: scroll.getSwapHighlightType,
      isGroupHighlighted: scroll.isGroupHighlighted,
      isHighlighted: scroll.isHighlighted,
      isSwapHighlighted: scroll.isSwapHighlighted,
    },
    lookups: {
      completeEventsForItem: data.getCompleteEventsForItem,
      completeSubgroupEvents: data.getCompleteSubgroupEvents,
      groupEvents: data.getGroupEvents,
      groupLocationLabel: (groupId: string): string | undefined => findGroup(groupId)?.locationLabel ?? undefined,
      ignoredAssets: ignoredAssetsState,
    },
  };

  // Mirrors the loaded events up to the view, which owns deletion and selection state. The
  // inversion is known debt: the view is meant to become the data owner, at which point this
  // watcher and the `update-event-ids` emit both go away.
  watch([data.events, data.completeEventsMapped, data.rawEvents], ([events, groupedEvents, rawEvents]) => {
    emit('update-event-ids', {
      eventIds: events.map(event => event.identifier),
      groupedEvents,
      rawEvents,
    });
  }, { immediate: true });

  return {
    redecode: {
      confirm: operations.confirmRedecode,
      hasCustomEvents: operations.hasCustomEvents,
      modelShow: operations.modelShowRedecodeConfirmation,
      payload: operations.redecodePayload,
      showIndexerOptions: operations.showIndexerOptions,
    },
    rowContext,
    shell: {
      entriesFoundTotal: data.entriesFoundTotal,
      found: data.found,
      groups: data.groups,
      loading: data.loading,
      showUpgradeRow: data.showUpgradeRow,
      total: data.total,
    },
    virtual: {
      containerProps: scroll.containerProps,
      list: scroll.virtualList,
      wrapperProps: scroll.wrapperProps,
    },
  };
}
