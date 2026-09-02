import type { MaybeRefOrGetter, Ref } from 'vue';
import type { PinnedName } from '@/modules/session/types';
import { startPromise } from '@shared/utils';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import { usePinnedHighlightNavigation } from '@/modules/shell/pinned/use-pinned-highlight-navigation';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

/** The query keys the matching panels own; both the yellow and the green highlight. */
const HIGHLIGHT_QUERY_KEYS = ['highlightedAssetMovement', 'highlightedPotentialMatch'];

/** The least a row needs for the panel to navigate to it. */
export interface PinnedMatchSubject {
  groupIdentifier: string;
}

interface PotentialMatchLocation {
  identifier: number;
  groupIdentifier: string;
}

export interface UsePinnedMatchPanelOptions<T extends PinnedMatchSubject> {
  /** Which pinned tab this panel occupies. */
  pinnedName: PinnedName;
  /** Row collections searched, in order, for the group the route asks to highlight. */
  sources: MaybeRefOrGetter<T[]>[];
  /** The event identifier a row highlights in the events table. */
  getIdentifier: (subject: T) => number;
  /** The group the route asks the panel to open on. */
  highlightedGroupIdentifier: () => string | undefined;
  /** The potential match the route asks the drawer to open on. */
  highlightedPotentialMatchIdentifier: () => number | undefined;
  /** The group that potential match belongs to. */
  potentialMatchGroupIdentifier: () => string | undefined;
}

export interface UsePinnedMatchPanelReturn<T extends PinnedMatchSubject> {
  /** The group currently highlighted in the panel's list. */
  activeGroupIdentifier: Readonly<Ref<string | undefined>>;
  /** The potential match currently highlighted in the drawer. */
  activePotentialMatchIdentifier: Readonly<Ref<number | undefined>>;
  /** The row whose potential matches the drawer is showing. */
  subject: Readonly<Ref<T | undefined>>;
  /** `v-model` for the detail sheet; closing routes through the same cleanup as the header button. */
  modelSheetOpen: Ref<boolean>;
  /** Reset local highlight state, clear the shared targets and strip the owned query keys. */
  clearHighlight: () => Promise<void>;
  /** Open the drawer on a row and highlight it in the events table. */
  select: (subject: T) => void;
  /** Close the drawer and drop the green highlight, keeping the yellow one. */
  closeDrawer: () => Promise<void>;
  /** Close the drawer and drop every highlight, after a match was made. */
  onMatched: () => Promise<void>;
  /** Drop every highlight, then remove the panel's tab. */
  unpin: () => Promise<void>;
  /** Highlight a row in the events table without opening the drawer. */
  showInHistoryEvents: (subject: T) => void;
  /** Highlight a potential match in the events table, keeping the row's own highlight. */
  showPotentialMatchInHistoryEvents: (data: PotentialMatchLocation, unmatchedIdentifier?: number) => void;
}

/**
 * The whole behaviour of a pinned matching panel: which row the drawer is on, which
 * highlights the events table is showing, and the navigation that keeps the two in step.
 *
 * `MatchAssetMovementsPinned` and `MatchBridgeTransactionsPinned` are the same panel over different
 * rows, and vary only in the collections they search, how a row names its event (an asset movement
 * must be unwrapped from its collection, a bridge transaction carries the identifier directly) and
 * the extra props their drawer content takes.
 */
export function usePinnedMatchPanel<T extends PinnedMatchSubject>(
  options: UsePinnedMatchPanelOptions<T>,
): UsePinnedMatchPanelReturn<T> {
  const {
    getIdentifier,
    highlightedGroupIdentifier,
    highlightedPotentialMatchIdentifier,
    pinnedName,
    potentialMatchGroupIdentifier,
    sources,
  } = options;

  const router = useRouter();
  const route = useRoute();

  const activeGroupIdentifier = shallowRef<string | undefined>(highlightedGroupIdentifier());
  const activePotentialMatchIdentifier = shallowRef<number | undefined>(highlightedPotentialMatchIdentifier());
  const subject = shallowRef<T>();
  const drawerOpen = shallowRef<boolean>(false);
  const hasNavigatedToInitialHighlight = shallowRef<boolean>(false);

  const { isPinned, unpin: unpinPanel } = usePinnedPanel(pinnedName);
  const { clearHighlightTarget, requestNavigation, setHighlightTarget } = useHistoryEventNavigation();

  const { clearHighlight } = usePinnedHighlightNavigation(
    HIGHLIGHT_QUERY_KEYS,
    () => {
      set(activeGroupIdentifier, undefined);
      set(activePotentialMatchIdentifier, undefined);
    },
    () => get(isPinned),
  );

  function highlightSubject(target: T): void {
    const identifier = getIdentifier(target);

    set(activeGroupIdentifier, target.groupIdentifier);
    set(activePotentialMatchIdentifier, undefined);

    clearHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH);
    setHighlightTarget(HighlightTargetTypes.ASSET_MOVEMENT, {
      groupIdentifier: target.groupIdentifier,
      identifier,
    });

    requestNavigation({
      highlightedAssetMovement: identifier,
      targetGroupIdentifier: target.groupIdentifier,
    });
  }

  function select(target: T): void {
    set(subject, target);
    set(drawerOpen, true);
    highlightSubject(target);
  }

  function showInHistoryEvents(target: T): void {
    highlightSubject(target);
  }

  async function closeDrawer(): Promise<void> {
    set(drawerOpen, false);
    set(subject, undefined);
    set(activePotentialMatchIdentifier, undefined);
    clearHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH);

    // Clear the green highlight from route while preserving the yellow highlight
    const { highlightedPotentialMatch, ...remainingQuery } = get(route).query;
    if (highlightedPotentialMatch) {
      await router.replace({ query: remainingQuery });
    }
  }

  const modelSheetOpen = computed<boolean>({
    get: () => get(drawerOpen) && !!get(subject),
    set: (value) => {
      if (!value)
        startPromise(closeDrawer());
    },
  });

  async function onMatched(): Promise<void> {
    await closeDrawer();
    await clearHighlight();
  }

  async function unpin(): Promise<void> {
    await clearHighlight();
    unpinPanel();
  }

  function showPotentialMatchInHistoryEvents(
    data: PotentialMatchLocation,
    unmatchedIdentifier?: number,
  ): void {
    set(activePotentialMatchIdentifier, data.identifier);
    setHighlightTarget(HighlightTargetTypes.POTENTIAL_MATCH, {
      groupIdentifier: data.groupIdentifier,
      identifier: data.identifier,
    });

    const yellowHighlight = unmatchedIdentifier
      ?? (Number(get(route).query.highlightedAssetMovement) || undefined);

    requestNavigation({
      highlightedAssetMovement: yellowHighlight,
      highlightedPotentialMatch: data.identifier,
      targetGroupIdentifier: data.groupIdentifier,
    });
  }

  function findSubject(targetGroupIdentifier: string): T | undefined {
    for (const source of sources) {
      const match = toValue(source).find(item => item.groupIdentifier === targetGroupIdentifier);
      if (match)
        return match;
    }
    return undefined;
  }

  /**
   * Navigate to the highlighted row if it has arrived.
   * Returns true if navigation was triggered, false otherwise.
   */
  function navigateToHighlighted(targetGroupIdentifier: string): boolean {
    const target = findSubject(targetGroupIdentifier);
    if (!target)
      return false;

    const potentialMatch = highlightedPotentialMatchIdentifier();
    const potentialMatchGroup = potentialMatchGroupIdentifier();

    if (potentialMatch && potentialMatchGroup) {
      set(subject, target);
      set(drawerOpen, true);
      set(activeGroupIdentifier, target.groupIdentifier);
      showPotentialMatchInHistoryEvents(
        { groupIdentifier: potentialMatchGroup, identifier: potentialMatch },
        getIdentifier(target),
      );
    }
    else {
      showInHistoryEvents(target);
    }
    return true;
  }

  // Watch for data to load and navigate to the initial highlight if one was provided
  watch(() => sources.map(source => toValue(source)), () => {
    const initialHighlight = highlightedGroupIdentifier();
    if (!initialHighlight || get(hasNavigatedToInitialHighlight))
      return;

    if (navigateToHighlighted(initialHighlight)) {
      set(hasNavigatedToInitialHighlight, true);
    }
  });

  // Watch for prop changes to handle navigation when the panel is already open
  watch(highlightedGroupIdentifier, (newHighlight, oldHighlight) => {
    // Only trigger if the highlight actually changed (not on initial mount)
    if (!newHighlight || newHighlight === oldHighlight)
      return;

    set(activeGroupIdentifier, newHighlight);
    navigateToHighlighted(newHighlight);
  });

  return {
    activeGroupIdentifier: readonly(activeGroupIdentifier),
    activePotentialMatchIdentifier: readonly(activePotentialMatchIdentifier),
    clearHighlight,
    closeDrawer,
    modelSheetOpen,
    onMatched,
    select,
    showInHistoryEvents,
    showPotentialMatchInHistoryEvents,
    subject: shallowReadonly(subject),
    unpin,
  };
}
