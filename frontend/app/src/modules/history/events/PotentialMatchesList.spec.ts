import type { PotentialMatchRow, UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PotentialMatchesList from '@/modules/history/events/PotentialMatchesList.vue';
import { createRuiPlugin } from '@/plugins/rui';

const entry = createMock<HistoryEventEntry>({ eventSubtype: 'deposit', identifier: 1 });

vi.mock('@/modules/history/event-utils', () => ({
  getEventEntryFromCollection: (): { entry: HistoryEventEntry } => ({ entry }),
}));

vi.mock('@/modules/history/management/forms/utils', () => ({
  getAssetMovementsType: (): string => 'deposit-label',
}));

const SubjectTableStub = {
  name: 'PotentialMatchSubjectTable',
  props: ['entry', 'typeLabel', 'locationHeader'],
  template: '<div />',
};

const EmptyStub = {
  emits: ['widen'],
  name: 'PotentialMatchesEmpty',
  props: ['hours', 'tolerance', 'canWiden', 'explanation'],
  template: '<button data-testid="stub-widen" @click="$emit(\'widen\')" />',
};

const movement = createMock<UnmatchedEventGroup>({ asset: 'ETH', groupIdentifier: '0xabc' });

const noMatches: PotentialMatchRow[] = [];

function createWrapper(props: Record<string, unknown> = {}): VueWrapper<any> {
  return mount(PotentialMatchesList, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        AmountInput: { name: 'AmountInput', props: ['modelValue'], template: '<div />' },
        PotentialMatchesCards: true,
        PotentialMatchesEmpty: EmptyStub,
        PotentialMatchesTable: true,
        PotentialMatchSubjectCard: true,
        PotentialMatchSubjectTable: SubjectTableStub,
      },
    },
    props: {
      loading: false,
      matches: noMatches,
      movement,
      onlyExpectedAssets: false,
      searchTimeRange: '24',
      selectedMatchIds: [],
      tolerancePercentage: '5',
      ...props,
    },
  });
}

function subject(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(SubjectTableStub);
}

describe('potentialMatchesList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Flows that are not asset movements relabel the type badge and the location column together, so
   * a caller that supplies neither gets the asset-movement wording for both.
   */
  describe('describing the unmatched entry', () => {
    it('should fall back to the asset movement type and the exchange header', () => {
      const wrapper = createWrapper();

      expect(subject(wrapper).props('typeLabel')).toBe('deposit-label');
      expect(subject(wrapper).props('locationHeader')).toBe('common.exchange');
    });

    it('should use the labels the caller supplied', () => {
      const wrapper = createWrapper({
        entryLabels: { locationHeader: 'Chain', type: 'Bridge out' },
      });

      expect(subject(wrapper).props('typeLabel')).toBe('Bridge out');
      expect(subject(wrapper).props('locationHeader')).toBe('Chain');
    });
  });

  describe('widening the search', () => {
    it('should double both criteria and search again', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=stub-widen]').trigger('click');

      expect(wrapper.emitted<[string]>('update:searchTimeRange')?.at(-1)?.[0]).toBe('48');
      expect(wrapper.emitted<[string]>('update:tolerancePercentage')?.at(-1)?.[0]).toBe('10');
      expect(wrapper.emitted('search')).toHaveLength(1);
    });

    it('should offer widening while a criterion has room', () => {
      const wrapper = createWrapper();

      expect(wrapper.findComponent(EmptyStub).props('canWiden')).toBe(true);
    });

    it('should stop offering it once both criteria are at their max', () => {
      const wrapper = createWrapper({ searchTimeRange: '168', tolerancePercentage: '100' });

      expect(wrapper.findComponent(EmptyStub).props('canWiden')).toBe(false);
    });
  });

  describe('the results', () => {
    it('should explain an empty result rather than showing a table', () => {
      const wrapper = createWrapper({ emptyExplanation: 'nothing within range' });

      expect(wrapper.findComponent(EmptyStub).exists()).toBe(true);
      expect(wrapper.findComponent(EmptyStub).props('explanation')).toBe('nothing within range');
    });

    it('should stop explaining while a search is still running', () => {
      const wrapper = createWrapper({ loading: true });

      expect(wrapper.findComponent(EmptyStub).exists()).toBe(false);
    });

    it('should show what the last search failed with', () => {
      const wrapper = createWrapper({ searchError: 'the backend said no' });

      expect(wrapper.text()).toContain('the backend said no');
    });

    it('should say nothing about a search that did not fail', () => {
      expect(createWrapper().text()).not.toContain('the backend said no');
    });
  });
});
