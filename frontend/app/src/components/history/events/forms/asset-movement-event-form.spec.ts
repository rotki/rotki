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
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('forms/AssetMovementEventForm.vue', () => {
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

  const group: AssetMovementEvent = {
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

  beforeAll(() => {
    setupDayjs();
    vi.useFakeTimers();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof AssetMovementEventForm> = {
    props: {
      data: { nextSequenceId: '0' },
    },
  }): VueWrapper<InstanceType<typeof AssetMovementEventForm>> =>
    mount(AssetMovementEventForm, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  describe('prefill the fields based on the props', () => {
    it('should show the default state when opening the form without any data', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe('');
      expect((wrapper.find('[data-cy=locationLabel] .input-value').element as HTMLInputElement).value).toBe('');
    });

    it('it should update the fields when all properties in data are updated', async () => {
      wrapper = createWrapper();
      vi.advanceTimersToNextTimer();
      await wrapper.setProps({ data: { event: group, eventsInGroup: [group] } });
      vi.advanceTimersToNextTimer();

      expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe(
        group.eventIdentifier,
      );

      expect((wrapper.find('[data-cy=locationLabel] .input-value').element as HTMLInputElement).value).toBe(
        group.locationLabel,
      );

      expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(
        group.amount.toString(),
      );

      expect(
        (wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').element as HTMLTextAreaElement).value,
      ).toBe(group.notes);
    });
  });

  it('should show eventTypes options correctly', async () => {
    wrapper = createWrapper({ props: { data: { eventsInGroup: [group] } } });
    vi.advanceTimersToNextTimer();
    await flushPromises();

    expect(wrapper.findAll('[data-cy=eventType] .selections span')).toHaveLength(2);
  });
});
