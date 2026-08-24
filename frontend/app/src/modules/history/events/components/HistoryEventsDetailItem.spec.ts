import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import HistoryEventsDetailItem from '@/modules/history/events/components/HistoryEventsDetailItem.vue';
import { provideHistoryEventsSelection } from '@/modules/history/events/use-history-events-selection-context';
import { useHistoryEventsSelectionMode } from '@/modules/history/events/use-selection-mode';

const event = createMock<HistoryEventEntry>({
  asset: 'ETH',
  autoNotes: 'Receive 1 ETH',
  eventSubtype: 'none',
  eventType: 'receive',
  identifier: 1,
  location: 'ethereum',
  sequenceIndex: 0,
});

/**
 * `provideSelection` mirrors what HistoryEventsView does. The row reads selection through inject
 * rather than a prop, so an embedding that provides nothing must still render, just without
 * checkboxes — that negative case is the point of the pair below.
 */
function mountItem(provideSelection: boolean): VueWrapper {
  return mount({
    components: { HistoryEventsDetailItem },
    setup() {
      if (provideSelection) {
        const selection = useHistoryEventsSelectionMode();
        selection.setAvailableIds([1]);
        selection.actions.toggle();
        provideHistoryEventsSelection(selection);
      }
      return { completeGroupEvents: [event], event };
    },
    template: '<HistoryEventsDetailItem :event="event" :index="0" :complete-group-events="completeGroupEvents" />',
  }, {
    global: {
      plugins: [createCustomPinia()],
      provide: libraryDefaults,
      // `shallow` would stub the component under test too; only its children should be stubs.
      stubs: { HistoryEventsDetailItem: false },
    },
    shallow: true,
  });
}

describe('modules/history/events/components/HistoryEventsDetailItem', () => {
  it('should render a checkbox when a provided selection is in selection mode', () => {
    const wrapper = mountItem(true);

    expect(wrapper.findComponent({ name: 'RuiCheckbox' }).exists()).toBe(true);
  });

  it('should render without a checkbox when no selection is provided', () => {
    const wrapper = mountItem(false);

    expect(wrapper.findComponent({ name: 'RuiCheckbox' }).exists()).toBe(false);
  });
});
