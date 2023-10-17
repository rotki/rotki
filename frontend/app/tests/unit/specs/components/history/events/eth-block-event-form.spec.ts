import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type EthBlockEvent } from '@/types/history/events';
import EthBlockEventForm from '@/components/history/events/forms/EthBlockEventForm.vue';

describe('EthBlockEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<EthBlockEventForm>;

  const groupHeader: EthBlockEvent = {
    identifier: 11336,
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    eventIdentifier: 'BP1_444',
    sequenceIndex: 0,
    timestamp: 1697442021000,
    location: 'ethereum',
    asset: 'ETH',
    balance: {
      amount: bigNumberify('100'),
      usdValue: bigNumberify('2000')
    },
    eventType: 'staking',
    eventSubtype: 'mev reward',
    locationLabel: '0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa',
    notes:
      'Validator 12 produced block 444 with 100 ETH going to 0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa as the mev reward',
    validatorIndex: 122,
    blockNumber: 444
  };

  const createWrapper = (options: ThisTypedMountOptions<any> = {}) => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(EthBlockEventForm, {
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
          wrapper.find('[data-cy=blockNumber] input')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=feeRecipient] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=isMevReward] input')
            .element as HTMLInputElement
        ).checked
      ).toBeFalsy();
    });

    test('`groupHeader` and `nextSequence` are passed', async () => {
      wrapper = createWrapper({
        propsData: {
          groupHeader
        }
      });
      await wrapper.vm.$nextTick();

      expect(
        (
          wrapper.find('[data-cy=blockNumber] input')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.blockNumber.toString());

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (
          wrapper.find('[data-cy=feeRecipient] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=isMevReward] input')
            .element as HTMLInputElement
        ).checked
      ).toBeFalsy();
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
          wrapper.find('[data-cy=blockNumber] input')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.blockNumber.toString());

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (
          wrapper.find('[data-cy=feeRecipient] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value
      ).toBe(groupHeader.balance.amount.toString());

      expect(
        (
          wrapper.find('[data-cy=isMevReward] input')
            .element as HTMLInputElement
        ).checked
      ).toBeTruthy();
    });
  });
});
