import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type EthWithdrawalEvent } from '@/types/history/events';
import EthWithdrawalEventForm from '@/components/history/events/forms/EthWithdrawalEventForm.vue';

describe('EthWithdrawalEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<EthWithdrawalEventForm>;

  const groupHeader: EthWithdrawalEvent = {
    identifier: 11343,
    entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
    eventIdentifier: 'EW_123_19647',
    sequenceIndex: 0,
    timestamp: 1697517629000,
    location: 'ethereum',
    asset: 'ETH',
    balance: {
      amount: bigNumberify('2.5'),
      usdValue: bigNumberify('3973.525')
    },
    eventType: 'staking',
    eventSubtype: 'remove asset',
    locationLabel: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    notes: 'Exited validator 123 with 2.5 ETH',
    validatorIndex: 123,
    isExit: true
  };

  const createWrapper = (options: ThisTypedMountOptions<any> = {}) => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(EthWithdrawalEventForm, {
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
        (
          wrapper.find('[data-cy=withdrawalAddress] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe('');

      expect(
        (wrapper.find('[data-cy=isExited] input').element as HTMLInputElement)
          .checked
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
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (
          wrapper.find('[data-cy=withdrawalAddress] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value
      ).toBe('');

      expect(
        (wrapper.find('[data-cy=isExited] input').element as HTMLInputElement)
          .checked
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
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (
          wrapper.find('[data-cy=withdrawalAddress] .input-value')
            .element as HTMLInputElement
        ).value
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value
      ).toBe(groupHeader.balance.amount.toString());

      expect(
        (wrapper.find('[data-cy=isExited] input').element as HTMLInputElement)
          .checked
      ).toBeTruthy();
    });
  });
});
