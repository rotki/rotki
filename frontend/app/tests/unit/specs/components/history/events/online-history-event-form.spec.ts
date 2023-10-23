import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import flushPromises from 'flush-promises';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type OnlineHistoryEvent } from '@/types/history/events';
import OnlineHistoryEventForm from '@/components/history/events/forms/OnlineHistoryEventForm.vue';
import VAutocompleteStub from '../../../stubs/VAutocomplete';
import VComboboxStub from '../../../stubs/VCombobox';

describe('OnlineHistoryEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<OnlineHistoryEventForm>;

  const groupHeader: OnlineHistoryEvent = {
    identifier: 449,
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventIdentifier: 'STJ6KRHJYGA',
    sequenceIndex: 20,
    timestamp: 1696741486185,
    location: 'kraken',
    asset: 'ETH',
    balance: {
      amount: bigNumberify(10),
      usdValue: bigNumberify(40)
    },
    eventType: 'staking',
    eventSubtype: 'reward',
    locationLabel: 'Kraken 1',
    notes: 'History event notes'
  };

  const createWrapper = (options: ThisTypedMountOptions<any> = {}) => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(OnlineHistoryEventForm, {
      pinia,
      vuetify,
      stubs: {
        VAutocomplete: VAutocompleteStub,
        VCombobox: VComboboxStub
      },
      ...options
    });
  };

  describe('should prefill the fields based on the props', () => {
    test('no `groupHeader`, `editableItem`, nor `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await wrapper.vm.$nextTick();

      expect(
        (wrapper.find('[data-cy=eventIdentifier]').element as HTMLInputElement)
          .value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe('0');
    });

    test('`groupHeader` and `nextSequence` are passed', async () => {
      wrapper = createWrapper({
        propsData: {
          groupHeader,
          nextSequence: '10'
        }
      });
      await wrapper.vm.$nextTick();

      expect(
        (wrapper.find('[data-cy=eventIdentifier]').element as HTMLInputElement)
          .value
      ).toBe(groupHeader.eventIdentifier);

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe('10');

      expect(
        (wrapper.find('[data-cy=notes]').element as HTMLInputElement).value
      ).toBe('');
    });

    test('`groupHeader`, `editableItem`, and `nextSequence` are passed', async () => {
      wrapper = createWrapper({
        propsData: {
          groupHeader,
          editableItem: groupHeader,
          nextSequence: '10'
        }
      });
      await wrapper.vm.$nextTick();

      expect(
        (wrapper.find('[data-cy=eventIdentifier]').element as HTMLInputElement)
          .value
      ).toBe(groupHeader.eventIdentifier);

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value
      ).toBe(groupHeader.balance.amount.toString());

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value.replace(',', '')
      ).toBe(groupHeader.sequenceIndex.toString());

      expect(
        (wrapper.find('[data-cy=notes]').element as HTMLInputElement).value
      ).toBe(groupHeader.notes);
    });
  });

  test('should show all eventTypes options correctly', async () => {
    wrapper = createWrapper({ propsData: { groupHeader } });
    await wrapper.vm.$nextTick();
    await flushPromises();

    const { historyEventTypesData } = useHistoryEventMappings();

    expect(
      wrapper.findAll('[data-cy=eventType] .selections span')
    ).toHaveLength(get(historyEventTypesData).length);
  });

  test('should show all eventSubTypes options correctly', async () => {
    wrapper = createWrapper({ propsData: { groupHeader } });
    await wrapper.vm.$nextTick();
    await flushPromises();

    const { historyEventSubTypesData } = useHistoryEventMappings();

    expect(
      wrapper.findAll('[data-cy=eventSubtype] .selections span')
    ).toHaveLength(get(historyEventSubTypesData).length);
  });

  test('should show correct eventSubtypes options, based on selected eventType', async () => {
    wrapper = createWrapper({ propsData: { groupHeader } });
    await wrapper.vm.$nextTick();
    await flushPromises();

    const { historyEventTypeGlobalMapping } = useHistoryEventMappings();

    const selectedEventType = 'deposit';

    await wrapper.find('[data-cy=eventType] .input-value').trigger('input', {
      value: selectedEventType
    });

    await wrapper.vm.$nextTick();

    const keysFromGlobalMappings = Object.keys(
      get(historyEventTypeGlobalMapping)?.[selectedEventType] ?? {}
    );

    const spans = await wrapper.findAll(
      '[data-cy=eventSubtype] .selections span'
    );
    expect(spans).toHaveLength(keysFromGlobalMappings.length);

    for (let i = 0; i < keysFromGlobalMappings.length; i++) {
      expect(keysFromGlobalMappings.includes(spans.at(i).text())).toBeTruthy();
    }
  });
});
