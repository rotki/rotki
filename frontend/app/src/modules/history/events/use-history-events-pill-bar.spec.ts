import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import {
  useHistoryEventsPillBar,
  type UseHistoryEventsPillBarReturn,
} from '@/modules/history/events/use-history-events-pill-bar';

const labels = { addFilter: 'Add filter' };

vi.mock('@/modules/core/table/pill/composables/use-pill-bar-labels', () => ({
  usePillBarLabels: (): unknown => computed(() => labels),
}));

function emptyToggles(): HistoryEventsToggles {
  return { matchExactEvents: false, showIgnoredAssets: false, stateMarkers: [] };
}

const filters = ref<MatchedKeywordWithBehaviour<any>>({});
const locationLabels = ref<string[]>([]);
const action = ref<string | undefined>();
const toggles = ref<HistoryEventsToggles>(emptyToggles());

interface Harness {
  wrapper: VueWrapper;
  bar: UseHistoryEventsPillBarReturn;
}

function mountBar(): Harness {
  let bar!: UseHistoryEventsPillBarReturn;
  const Comp = defineComponent({
    setup(): () => null {
      bar = useHistoryEventsPillBar({ action, filters, locationLabels, toggles });
      return (): null => null;
    },
  });
  const wrapper = mount(Comp);
  return { bar, wrapper };
}

describe('useHistoryEventsPillBar', () => {
  beforeEach(() => {
    set(filters, {});
    set(locationLabels, []);
    set(action, undefined);
    set(toggles, emptyToggles());
  });

  describe('what the bar is handed', () => {
    it('should send no params while nothing is filtered', () => {
      const { bar } = mountBar();

      expect(get(bar.modelPillParams)).toStrictEqual({});
    });

    it('should send a param for each filter that has a value', () => {
      set(action, 'deposit');
      set(locationLabels, ['kraken', 'coinbase']);
      set(toggles, { matchExactEvents: false, showIgnoredAssets: true, stateMarkers: ['customized'] });
      const { bar } = mountBar();

      expect(get(bar.modelPillParams)).toStrictEqual({
        action: 'deposit',
        locationLabels: ['kraken', 'coinbase'],
        showIgnoredAssets: true,
        stateMarkers: ['customized'],
      });
    });

    it('should leave the show-ignored param out rather than send it as false', () => {
      set(toggles, { matchExactEvents: false, showIgnoredAssets: false, stateMarkers: [] });
      const { bar } = mountBar();

      expect(get(bar.modelPillParams)).not.toHaveProperty('showIgnoredAssets');
    });

    it('should send an empty action, since that is a value the pill can hold', () => {
      set(action, '');
      const { bar } = mountBar();

      expect(get(bar.modelPillParams)).toStrictEqual({ action: '' });
    });

    it('should not send the match-exact toggle, which is not a pill', () => {
      set(toggles, { matchExactEvents: true, showIgnoredAssets: false, stateMarkers: [] });
      const { bar } = mountBar();

      expect(get(bar.modelPillParams)).toStrictEqual({});
    });
  });

  describe('what the bar writes back', () => {
    it('should push each param into the model behind it', () => {
      const { bar } = mountBar();

      set(bar.modelPillParams, {
        action: 'withdrawal',
        locationLabels: ['kraken'],
        showIgnoredAssets: true,
        stateMarkers: ['customized'],
      });

      expect(get(action)).toBe('withdrawal');
      expect(get(locationLabels)).toStrictEqual(['kraken']);
      expect(get(toggles)).toStrictEqual({
        matchExactEvents: false,
        showIgnoredAssets: true,
        stateMarkers: ['customized'],
      });
    });

    it('should clear every model an absent param stands for', () => {
      set(action, 'deposit');
      set(locationLabels, ['kraken']);
      set(toggles, { matchExactEvents: true, showIgnoredAssets: true, stateMarkers: ['customized'] });
      const { bar } = mountBar();

      set(bar.modelPillParams, {});

      expect(get(action)).toBeUndefined();
      expect(get(locationLabels)).toStrictEqual([]);
      expect(get(toggles)).toStrictEqual({
        matchExactEvents: true,
        showIgnoredAssets: false,
        stateMarkers: [],
      });
    });

    it('should accept a single value where a list is expected', () => {
      const { bar } = mountBar();

      set(bar.modelPillParams, { locationLabels: 'kraken', stateMarkers: 'customized' });

      expect(get(locationLabels)).toStrictEqual(['kraken']);
      expect(get(toggles).stateMarkers).toStrictEqual(['customized']);
    });

    it('should drop a state marker the app does not know', () => {
      const { bar } = mountBar();

      set(bar.modelPillParams, { stateMarkers: ['customized', 'not-a-state'] });

      expect(get(toggles).stateMarkers).toStrictEqual(['customized']);
    });

    it('should refuse a boolean where a string or list is expected', () => {
      set(action, 'deposit');
      set(locationLabels, ['kraken']);
      const { bar } = mountBar();

      set(bar.modelPillParams, { action: true, locationLabels: true, stateMarkers: true });

      expect(get(action)).toBeUndefined();
      expect(get(locationLabels)).toStrictEqual([]);
      expect(get(toggles).stateMarkers).toStrictEqual([]);
    });
  });

  describe('the match-exact toggle', () => {
    it('should flip it without disturbing the other toggles', () => {
      set(toggles, { matchExactEvents: false, showIgnoredAssets: true, stateMarkers: ['customized'] });
      const { bar } = mountBar();

      bar.toggleMatchExact();

      expect(get(toggles)).toStrictEqual({
        matchExactEvents: true,
        showIgnoredAssets: true,
        stateMarkers: ['customized'],
      });

      bar.toggleMatchExact();

      expect(get(toggles).matchExactEvents).toBe(false);
    });
  });

  describe('saved views', () => {
    it('should store the matches and the params together', () => {
      const matches = { asset: 'ETH' };
      set(filters, matches);
      set(action, 'deposit');
      const { bar } = mountBar();

      expect(get(bar.pillState)).toStrictEqual({ matches, params: { action: 'deposit' } });
    });

    it('should restore both from a view', () => {
      set(action, 'deposit');
      set(locationLabels, ['kraken']);
      const { bar } = mountBar();
      const view = createMock<SavedView>({
        matches: { asset: 'BTC' },
        params: { locationLabels: ['coinbase'] },
      });

      bar.applyView(view);

      expect(get(filters)).toStrictEqual({ asset: 'BTC' });
      expect(get(locationLabels)).toStrictEqual(['coinbase']);
      expect(get(action)).toBeUndefined();
    });
  });

  it('should hand the bar its own labels', () => {
    const { bar } = mountBar();

    expect(get(bar.pillLabels)).toStrictEqual(labels);
  });
});
