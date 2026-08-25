import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { SavedViewState } from '@/modules/core/table/pill/composables/use-saved-views';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import type { PillBarLabels } from '@/modules/core/table/pill/core/types';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import { arrayify } from '@/modules/core/common/data/array';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import { isValidHistoryEventState } from '@/modules/history/events/mapping/use-history-event-state-mapping';

/** What the bar puts in, and reads out of, its param bag. */
type PillParams = Record<string, string | string[] | boolean>;

export interface UseHistoryEventsPillBarOptions {
  /** The keyword matches the bar owns outright. */
  filters: Ref<MatchedKeywordWithBehaviour<any>>;
  /** The accounts pill, which the page also reads on its own. */
  locationLabels: Ref<string[]>;
  /** The action pill. */
  action: Ref<string | undefined>;
  /** The toggles behind the state and show-ignored pills, plus match-exact, which is not a pill. */
  toggles: Ref<HistoryEventsToggles>;
}

export interface UseHistoryEventsPillBarReturn {
  /** The bar's own labels. */
  pillLabels: ComputedRef<PillBarLabels>;
  /** `v-model:params` for the bar, bridged to the page's models. */
  modelPillParams: WritableComputedRef<PillParams>;
  /** What a saved view stores: the bar's two models under a name. */
  pillState: ComputedRef<SavedViewState>;
  /** Restore both models from a saved view. */
  applyView: (view: SavedView) => void;
  /** Constrain the active filters to the events themselves rather than their whole group. */
  toggleMatchExact: () => void;
}

/**
 * The bridge between the pill bar's param bag and the models the events page keeps.
 *
 * The account, state and show-ignored filters are param-bound pills (paramKeys `locationLabels`,
 * `stateMarkers`, `showIgnoredAssets`). An absent param clears its model, which for the boolean is
 * the pill's whole state: removing it is how it is turned off.
 */
export function useHistoryEventsPillBar(
  options: UseHistoryEventsPillBarOptions,
): UseHistoryEventsPillBarReturn {
  const { action, filters, locationLabels, toggles } = options;

  const pillLabels = usePillBarLabels();

  // Not a pill: it constrains how the other filters apply instead of filtering anything itself.
  function toggleMatchExact(): void {
    set(toggles, { ...get(toggles), matchExactEvents: !get(toggles).matchExactEvents });
  }

  const modelPillParams = computed<PillParams>({
    get(): PillParams {
      const labels = get(locationLabels);
      const { showIgnoredAssets, stateMarkers } = get(toggles);
      const result: PillParams = {};
      const verb = get(action);
      if (verb !== undefined)
        result.action = verb;
      if (labels.length > 0)
        result.locationLabels = labels;
      if (stateMarkers.length > 0)
        result.stateMarkers = stateMarkers;
      if (showIgnoredAssets)
        result.showIgnoredAssets = true;
      return result;
    },
    set(value: PillParams): void {
      const nextAction = value.action;
      set(action, typeof nextAction === 'string' ? nextAction : undefined);

      const nextLabels = value.locationLabels;
      set(locationLabels, nextLabels === undefined || typeof nextLabels === 'boolean' ? [] : arrayify(nextLabels));

      const nextMarkers = value.stateMarkers;
      set(toggles, {
        ...get(toggles),
        showIgnoredAssets: value.showIgnoredAssets === true,
        stateMarkers: nextMarkers === undefined || typeof nextMarkers === 'boolean'
          ? []
          : arrayify(nextMarkers).filter(isValidHistoryEventState),
      });
    },
  });

  // A saved view is the bar's two models under a name, so it both reads from and writes to the
  // same pair the bar is bound to.
  const pillState = computed<SavedViewState>(() => ({
    matches: get(filters),
    params: get(modelPillParams),
  }));

  function applyView(view: SavedView): void {
    set(filters, view.matches);
    set(modelPillParams, view.params);
  }

  return {
    applyView,
    modelPillParams,
    pillLabels,
    pillState,
    toggleMatchExact,
  };
}
