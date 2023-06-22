import { type Wrapper, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import flushPromises from 'flush-promises';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';

describe('HistoryEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<HistoryEventForm>;

  const transaction = {
    identifier: 14344,
    eventIdentifier:
      '10x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
    sequenceIndex: 2411,
    timestamp: 1686495083,
    location: 'ethereum',
    asset: 'eip155:1/erc20:0xA3Ee8CEB67906492287FFD256A9422313B5796d4',
    balance: {
      amount: '610',
      usdValue: '0'
    },
    eventType: 'receive',
    eventSubtype: null,
    locationLabel: '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
    notes:
      'Receive 610 Visit https://rafts.cc to claim rewards. from 0x30a2EBF10f34c6C4874b0bDD5740690fD2f3B70C to 0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
    entryType: 'evm event',
    address: '0x30a2EBF10f34c6C4874b0bDD5740690fD2f3B70C',
    counterparty: null,
    product: null,
    txHash:
      '0x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
    groupedEventsNum: 1
  };

  const createWrapper = () => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(HistoryEventForm, {
      pinia,
      vuetify,
      stubs: {
        VAutocomplete: {
          template: `
            <div>
              <div>
                <input :value="value" class="input-value" type="text" @input="$emit('input', $event.value)">
              </div>
              <div class="selections">
                <span v-for="item in items">
                  {{ item[itemValue] ?? item }}
                </span>
              </div>
            </div>
          `,
          props: {
            value: { type: String },
            items: { type: Array<any> },
            itemValue: { type: String }
          }
        },
        VCombobox: {
          template: `
            <div>
              <div>
                <input :value="value" class="input-value" type="text" @input="$emit('input', $event.value)">
              </div>
              <div class="selections">
                <span v-for="item in items">
                  {{ item }}
                </span>
              </div>
            </div>
          `,
          props: {
            value: { type: String },
            items: { type: Array<any> }
          }
        }
      },
      propsData: {
        transaction
      }
    });
  };

  test('should show all eventTypes options correctly', async () => {
    wrapper = createWrapper();
    await wrapper.vm.$nextTick();
    await flushPromises();

    const { historyEventTypesData } = useHistoryEventMappings();

    expect(
      wrapper.findAll('[data-cy=eventType] .selections span')
    ).toHaveLength(get(historyEventTypesData).length);
  });

  test('should show all eventSubTypes options correctly', async () => {
    wrapper = createWrapper();
    await wrapper.vm.$nextTick();
    await flushPromises();

    const { historyEventSubTypesData } = useHistoryEventMappings();

    expect(
      wrapper.findAll('[data-cy=eventSubtype] .selections span')
    ).toHaveLength(get(historyEventSubTypesData).length);
  });

  test('should show all counterparties options correctly', async () => {
    wrapper = createWrapper();
    await wrapper.vm.$nextTick();
    await flushPromises();

    const { counterparties } = useHistoryEventMappings();

    expect(
      wrapper.findAll('[data-cy=counterparty] .selections span')
    ).toHaveLength(get(counterparties).length);
  });

  test('should show correct eventSubtypes options, based on selected eventType and counterparty', async () => {
    wrapper = createWrapper();
    await wrapper.vm.$nextTick();
    await flushPromises();

    const {
      historyEventTypeGlobalMapping,
      historyEventTypePerProtocolMapping
    } = useHistoryEventMappings();

    const selectedEventType = 'deposit';

    await wrapper.find('[data-cy=eventType] .input-value').trigger('input', {
      value: selectedEventType
    });

    await wrapper.vm.$nextTick();

    const keysFromGlobalMappings = Object.keys(
      get(historyEventTypeGlobalMapping)[selectedEventType]
    );

    let spans = await wrapper.findAll(
      '[data-cy=eventSubtype] .selections span'
    );
    expect(spans).toHaveLength(keysFromGlobalMappings.length);

    for (let i = 0; i < keysFromGlobalMappings.length; i++) {
      expect(keysFromGlobalMappings.includes(spans.at(i).text())).toBeTruthy();
    }

    // should not add eventSubtype options, if the selectedCounterparty doesn't has that eventType.
    await wrapper.find('[data-cy=counterparty] .input-value').trigger('input', {
      value: '1inch'
    });

    await wrapper.vm.$nextTick();
    expect(spans).toHaveLength(keysFromGlobalMappings.length);

    // should not add eventSubtype options from perProtocolMappings, if the selectedCounterparty has that eventType.
    const selectedCounterparty = 'yearn-v2';
    await wrapper.find('[data-cy=counterparty] .input-value').trigger('input', {
      value: selectedCounterparty
    });

    await wrapper.vm.$nextTick();

    const keysFromPerProtocolMappings = Object.keys(
      get(historyEventTypePerProtocolMapping).ethereum[selectedCounterparty][
        selectedEventType
      ]
    );

    const joinKeys = [
      ...keysFromGlobalMappings,
      ...keysFromPerProtocolMappings
    ].filter(uniqueStrings);

    spans = wrapper.findAll('[data-cy=eventSubtype] .selections span');
    expect(spans).toHaveLength(joinKeys.length);

    for (let i = 0; i < joinKeys.length; i++) {
      expect(joinKeys.includes(spans.at(i).text())).toBeTruthy();
    }
  });

  test('should show product options, based on selected counterparty', async () => {
    wrapper = createWrapper();
    await wrapper.vm.$nextTick();
    await flushPromises();

    expect(wrapper.find('[data-cy=product]').attributes('disabled')).toBe(
      'disabled'
    );

    // input is still disabled, if the counterparty doesn't have mapped products.
    await wrapper.find('[data-cy=counterparty] .input-value').trigger('input', {
      value: '1inch'
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-cy=product]').attributes('disabled')).toBe(
      'disabled'
    );

    // products options should be showed correctly, if the counterparty have mapped products.
    const selectedCounterparty = 'convex';
    await wrapper.find('[data-cy=counterparty] .input-value').trigger('input', {
      value: selectedCounterparty
    });
    await wrapper.vm.$nextTick();

    const { historyEventProductsMapping } = useHistoryEventMappings();

    const products = get(historyEventProductsMapping)[selectedCounterparty];

    const spans = wrapper.findAll('[data-cy=product] .selections span');
    expect(spans).toHaveLength(products.length);

    for (let i = 0; i < products.length; i++) {
      expect(products.includes(spans.at(i).text())).toBeTruthy();
    }
  });
});
