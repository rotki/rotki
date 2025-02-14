import { type ComponentMountingOptions, type VueWrapper, mount } from '@vue/test-utils';
import { type Pinia, createPinia, setActivePinia } from 'pinia';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { HistoryEventEntryType } from '@rotki/common';
import EthWithdrawalEventForm from '@/components/history/events/forms/EthWithdrawalEventForm.vue';
import { setupDayjs } from '@/utils/date';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import type { AssetMap } from '@/types/asset';
import type { EthWithdrawalEvent } from '@/types/history/events';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('ethWithdrawalEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EthWithdrawalEventForm>>;
  let pinia: Pinia;

  const asset = {
    name: 'Ethereum',
    symbol: 'ETH',
    assetType: 'own chain',
    isCustomAsset: false,
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const groupHeader: EthWithdrawalEvent = {
    identifier: 11343,
    entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
    eventIdentifier: 'EW_123_19647',
    sequenceIndex: 0,
    timestamp: 1697517629000,
    location: 'ethereum',
    asset: asset.symbol,
    amount: bigNumberify('2.5'),
    eventType: 'staking',
    eventSubtype: 'remove asset',
    locationLabel: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    notes: 'Exit validator 123 with 2.5 ETH',
    validatorIndex: 123,
    isExit: true,
  };

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
    vi.useFakeTimers();
  });

  beforeEach(() => {
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof EthWithdrawalEventForm> = {}) =>
    mount(EthWithdrawalEventForm, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  describe('should prefill the fields based on the props', () => {
    it('no `groupHeader`, nor `editableItem` are passed', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=withdrawalAddress] .input-value').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=isExited] input').element as HTMLInputElement).checked).toBeFalsy();
    });

    it('`groupHeader` passed', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ groupHeader });

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(
        groupHeader.validatorIndex.toString(),
      );

      expect((wrapper.find('[data-cy=withdrawalAddress] .input-value').element as HTMLInputElement).value).toBe(
        groupHeader.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe('0');

      expect((wrapper.find('[data-cy=isExited] input').element as HTMLInputElement).checked).toBeFalsy();
    });

    it('`groupHeader` and `editableItem` are passed', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ groupHeader, editableItem: groupHeader });

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(
        groupHeader.validatorIndex.toString(),
      );

      expect((wrapper.find('[data-cy=withdrawalAddress] .input-value').element as HTMLInputElement).value).toBe(
        groupHeader.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(
        groupHeader.amount.toString(),
      );

      expect((wrapper.find('[data-cy=isExited] input').element as HTMLInputElement).checked).toBeTruthy();
    });
  });
});
