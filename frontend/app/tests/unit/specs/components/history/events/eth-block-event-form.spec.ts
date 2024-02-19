import {
  type ComponentMountingOptions,
  type VueWrapper,
  mount,
} from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createVuetify } from 'vuetify';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import EthBlockEventForm from '@/components/history/events/forms/EthBlockEventForm.vue';
import VAutocompleteStub from '../../../stubs/VAutocomplete';
import VComboboxStub from '../../../stubs/VCombobox';
import type { EthBlockEvent } from '@/types/history/events';

describe('ethBlockEventForm.vue', () => {
  setupDayjs();
  let wrapper: VueWrapper<InstanceType<typeof EthBlockEventForm>>;

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
      usdValue: bigNumberify('2000'),
    },
    eventType: 'staking',
    eventSubtype: 'mev reward',
    locationLabel: '0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa',
    notes:
      'Validator 12 produced block 444 with 100 ETH going to 0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa as the mev reward',
    validatorIndex: 122,
    blockNumber: 444,
  };

  const createWrapper = (options: ComponentMountingOptions<typeof EthBlockEventForm> = {}) => {
    const vuetify = createVuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(EthBlockEventForm, {

      global: {
        plugins: [pinia, vuetify],
        stubs: {
          VAutocomplete: VAutocompleteStub,
          VCombobox: VComboboxStub,
        },
      },
      ...options,
    });
  };

  describe('should prefill the fields based on the props', () => {
    it('no `groupHeader`, `editableItem`, nor `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();

      expect(
        (
          wrapper.find('[data-cy=blockNumber] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=feeRecipient] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=isMevReward] input')
            .element as HTMLInputElement
        ).checked,
      ).toBeFalsy();
    });

    it('`groupHeader` and `nextSequence` are passed', async () => {
      wrapper = createWrapper({
        props: {
          groupHeader,
        },
      });
      await nextTick();

      expect(
        (
          wrapper.find('[data-cy=blockNumber] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.blockNumber.toString());

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (
          wrapper.find('[data-cy=feeRecipient] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=isMevReward] input')
            .element as HTMLInputElement
        ).checked,
      ).toBeFalsy();
    });

    it('`groupHeader`, `editableItem`, and `nextSequence` are passed', async () => {
      wrapper = createWrapper({
        props: {
          groupHeader,
          editableItem: groupHeader,
        },
      });
      await nextTick();

      expect(
        (
          wrapper.find('[data-cy=blockNumber] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.blockNumber.toString());

      expect(
        (
          wrapper.find('[data-cy=validatorIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.validatorIndex.toString());

      expect(
        (
          wrapper.find('[data-cy=feeRecipient] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.locationLabel);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value,
      ).toBe(groupHeader.balance.amount.toString());

      expect(
        (
          wrapper.find('[data-cy=isMevReward] input')
            .element as HTMLInputElement
        ).checked,
      ).toBeTruthy();
    });
  });
});
