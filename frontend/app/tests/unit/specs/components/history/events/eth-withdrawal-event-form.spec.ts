import type { AssetMap } from '@/types/asset';
import type { EthWithdrawalEvent } from '@/types/history/events';
import EthWithdrawalEventForm from '@/components/history/events/forms/EthWithdrawalEventForm.vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useBalancePricesStore } from '@/store/balances/prices';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('forms/EthWithdrawalEventForm.vue', () => {
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

  const group: EthWithdrawalEvent = {
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
    it('should show the default state when opening the form without any data', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=withdrawalAddress] .input-value').element as HTMLInputElement).value).toBe('');

      expect((wrapper.find('[data-cy=isExited] input').element as HTMLInputElement).checked).toBeFalsy();
    });

    it('should update the fields when `group` updated', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ data: { group } });

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(
        group.validatorIndex.toString(),
      );

      expect((wrapper.find('[data-cy=withdrawalAddress] .input-value').element as HTMLInputElement).value).toBe(
        group.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe('0');

      expect((wrapper.find('[data-cy=isExited] input').element as HTMLInputElement).checked).toBeFalsy();
    });

    it('it should update the fields when all properties in data are updated', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ data: { group, event: group } });

      expect((wrapper.find('[data-cy=validatorIndex] input').element as HTMLInputElement).value).toBe(
        group.validatorIndex.toString(),
      );

      expect((wrapper.find('[data-cy=withdrawalAddress] .input-value').element as HTMLInputElement).value).toBe(
        group.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(
        group.amount.toString(),
      );

      expect((wrapper.find('[data-cy=isExited] input').element as HTMLInputElement).checked).toBeTruthy();
    });
  });
});
