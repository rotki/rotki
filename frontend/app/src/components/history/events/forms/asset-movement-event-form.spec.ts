import type { AssetMap } from '@/types/asset';
import type { AssetMovementEvent } from '@/types/history/events';
import AssetMovementEventForm from '@/components/history/events/forms/AssetMovementEventForm.vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useBalancePricesStore } from '@/store/balances/prices';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('forms/AssetMovementEventForm.vue', () => {
  setupDayjs();
  let wrapper: VueWrapper<InstanceType<typeof AssetMovementEventForm>>;
  let pinia: Pinia;

  const asset = {
    assetType: 'own chain',
    isCustomAsset: false,
    name: 'Ethereum',
    symbol: 'ETH',
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const groupHeader: AssetMovementEvent = {
    amount: bigNumberify(10),
    asset: asset.symbol,
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventIdentifier: 'STJ6KRHJYGA',
    eventSubtype: 'remove asset',
    eventType: 'withdrawal',
    extraData: null,
    identifier: 449,
    location: 'kraken',
    locationLabel: 'Kraken 1',
    notes: 'History event notes',
    sequenceIndex: 20,
    timestamp: 1696741486185,
  };

  beforeEach(() => {
    vi.useFakeTimers();
    pinia = createPinia();
    setActivePinia(pinia);
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof AssetMovementEventForm> = {}): VueWrapper<InstanceType<typeof AssetMovementEventForm>> =>
    mount(AssetMovementEventForm, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  describe('prefill the fields based on the props', () => {
    it('should have empty fields when no `groupEvents` nor `editableItem` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();

      expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe('');
      expect((wrapper.find('[data-cy=locationLabel] .input-value').element as HTMLInputElement).value).toBe('');
    });

    it('should show the proper data when `groupHeader` and `editableItem` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();
      await wrapper.setProps({ editableItem: groupHeader, groupEvents: [groupHeader] });
      await nextTick();

      expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe(
        groupHeader.eventIdentifier,
      );

      expect((wrapper.find('[data-cy=locationLabel] .input-value').element as HTMLInputElement).value).toBe(
        groupHeader.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(
        groupHeader.amount.toString(),
      );

      expect(
        (wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').element as HTMLTextAreaElement).value,
      ).toBe(groupHeader.notes);
    });
  });

  it('should show eventTypes options correctly', async () => {
    wrapper = createWrapper({ props: { groupEvents: [groupHeader] } });
    await nextTick();
    await flushPromises();

    expect(wrapper.findAll('[data-cy=eventType] .selections span')).toHaveLength(2);
  });
});
