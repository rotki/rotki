import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type EthDepositEvent } from '@/types/history/events';
import EthDepositEventForm from '@/components/history/events/forms/EthDepositEventForm.vue';

describe('EthDepositEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<EthDepositEventForm>;

  const groupHeader: EthDepositEvent = {
    identifier: 11344,
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    eventIdentifier:
      '10x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    sequenceIndex: 12,
    timestamp: 1697522243000,
    location: 'ethereum',
    asset: 'ETH',
    balance: {
      amount: bigNumberify('3.2'),
      usdValue: bigNumberify('5082.048')
    },
    eventType: 'staking',
    eventSubtype: 'deposit asset',
    locationLabel: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    notes: 'Deposit 3.2 ETH to validator 223',
    txHash:
      '0x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    counterparty: 'eth2',
    product: 'staking',
    address: '0x00000000219ab540356cBB839Cbe05303d7705Fa',
    validatorIndex: 223
  };

  const createWrapper = (options: ThisTypedMountOptions<any> = {}) => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(EthDepositEventForm, {
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
      ...options
    });
  };

  describe('should prefill the fields based on the props', () => {
    test('no `groupHeader`, `editableItem`, nor `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await wrapper.vm.$nextTick();

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (wrapper.find('[data-cy=txHash]').element as HTMLInputElement).value
      ).toBe('');

      expect(wrapper.find('[data-cy=eventIdentifier]').exists()).toBeFalsy();

      expect(
        (
          wrapper.find('[data-cy=depositor] .input-value')
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
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (wrapper.find('[data-cy=txHash]').element as HTMLInputElement).value
      ).toBe(groupHeader.txHash);

      expect(wrapper.find('[data-cy=eventIdentifier]').exists()).toBeFalsy();

      expect(
        (
          wrapper.find('[data-cy=depositor] .input-value')
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
    });

    test('`groupHeader`, `editableItem`, and `nextSequence` are passed', async () => {
      wrapper = createWrapper({
        propsData: {
          groupHeader,
          editableItem: groupHeader
        }
      });
      await wrapper.vm.$nextTick();

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (wrapper.find('[data-cy=txHash]').element as HTMLInputElement).value
      ).toBe(groupHeader.txHash);

      expect(
        (wrapper.find('[data-cy=eventIdentifier]').element as HTMLInputElement)
          .value
      ).toBe(groupHeader.eventIdentifier);

      expect(
        (
          wrapper.find('[data-cy=depositor] .input-value')
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
    });
  });
});
