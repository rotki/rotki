import type { PotentialMatchRow } from '@/modules/history/events/matching/types';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PotentialMatchesCards from '@/modules/history/events/PotentialMatchesCards.vue';
import PotentialMatchesTable from '@/modules/history/events/PotentialMatchesTable.vue';

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): Record<string, (value: string) => string> => ({
    getHistoryEventSubTypeName: (value: string): string => value,
    getHistoryEventTypeName: (value: string): string => value,
  }),
}));

/** The children below only display an entry; stubbing them keeps the spec on selection and wiring. */
const stubs = {
  DateDisplay: true,
  HashLink: true,
  HistoryEventAccount: true,
  HistoryEventAsset: true,
  LocationIcon: true,
};

function createRow(identifier: number, isCloseMatch = false): PotentialMatchRow {
  return {
    entry: createMock<HistoryEventEntry>({
      eventSubtype: 'receive',
      eventType: 'receive',
      groupIdentifier: `group-${identifier}`,
      identifier,
      location: 'kraken',
      timestamp: 1700000000000,
    }),
    identifier,
    isCloseMatch,
  };
}

const selected = ref<number[]>([]);

type Layout = typeof PotentialMatchesCards | typeof PotentialMatchesTable;

function mountLayout(layout: Layout, matches: PotentialMatchRow[]): VueWrapper {
  return mount(layout, {
    global: { provide: libraryDefaults, stubs },
    props: {
      'emptyLabel': 'Nothing found',
      matches,
      'maxHeight': '20rem',
      'onUpdate:selectedIds': (value: number[]): void => set(selected, value),
      'selectedIds': get(selected),
    },
  });
}

describe('modules/history/events/PotentialMatchesTable', () => {
  beforeEach(() => {
    set(selected, []);
  });

  it('should render a row per match', () => {
    const wrapper = mountLayout(PotentialMatchesTable, [createRow(1), createRow(2)]);

    expect(wrapper.findAll('[data-testid=potential-match-select]')).toHaveLength(2);
  });

  it('should show the empty label when a search returns nothing', () => {
    const wrapper = mountLayout(PotentialMatchesTable, []);

    expect(wrapper.text()).toContain('Nothing found');
  });

  it('should flag a close match as recommended', () => {
    const wrapper = mountLayout(PotentialMatchesTable, [createRow(1, true), createRow(2)]);

    expect(wrapper.findAllComponents({ name: 'RecommendedMatchIcon' })).toHaveLength(1);
  });

  /**
   * The table and the cards are the two halves of one fork, picked by `isPinned` in the host.
   * Anything a caller relies on has to behave the same in both, so both are driven here rather
   * than only the layout whoever wrote the change happened to have open.
   */
  describe('parity with the card layout', () => {
    const layouts: [string, Layout][] = [
      ['cards', PotentialMatchesCards],
      ['table', PotentialMatchesTable],
    ];

    it.each(layouts)('should select and deselect a match in the %s layout', async (_name, layout) => {
      const wrapper = mountLayout(layout, [createRow(1), createRow(2)]);

      await wrapper.find('[data-testid=potential-match-select][data-key="2"]').trigger('click');

      expect(get(selected)).toEqual([2]);

      await wrapper.setProps({ selectedIds: get(selected) });
      await wrapper.find('[data-testid=potential-match-select][data-key="2"]').trigger('click');

      expect(get(selected)).toEqual([]);
    });

    it.each(layouts)('should ask for the event in history from the %s layout, when the button element itself is clicked rather than the tooltip that is its component root', async (_name, layout) => {
      const wrapper = mountLayout(layout, [createRow(7)]);

      await wrapper.findComponent({ name: 'ShowInEventsButton' }).find('button').trigger('click');

      expect(wrapper.emitted('show-in-events')).toEqual([[{ groupIdentifier: 'group-7', identifier: 7 }]]);
    });
  });
});
