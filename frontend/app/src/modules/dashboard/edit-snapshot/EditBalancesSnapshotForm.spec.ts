import type { BalanceSnapshotPayload } from '@/modules/dashboard/snapshots';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { BalanceType } from '@/modules/balances/types/balances';
import EditBalancesSnapshotAssetPriceForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotAssetPriceForm.vue';
import EditBalancesSnapshotForm from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotForm.vue';

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: vi.fn(),
  }),
}));

interface BalanceSnapshotPayloadAndLocation extends BalanceSnapshotPayload {
  location: string;
}

type FormInstance = InstanceType<typeof EditBalancesSnapshotForm>;

describe('edit-snapshot/EditBalancesSnapshotForm.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<FormInstance>;

  const timestamp = 1700000000;

  const baseModel = (): BalanceSnapshotPayloadAndLocation => ({
    amount: '1.5',
    assetIdentifier: 'ETH',
    category: BalanceType.ASSET,
    location: 'blockchain',
    timestamp,
    usdValue: '3000',
  });

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(usePriceTaskManager().getHistoricPrice).mockResolvedValue(bigNumberify(2000));
    vi.mocked(useAssetPricesApi().addHistoricalPrice).mockResolvedValue(true);
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(modelValue: BalanceSnapshotPayloadAndLocation = baseModel()): VueWrapper<FormInstance> {
    const model = ref<BalanceSnapshotPayloadAndLocation>(modelValue);
    return mount(EditBalancesSnapshotForm, {
      global: {
        plugins: [pinia],
      },
      props: {
        'locations': ['blockchain', 'kraken'],
        'modelValue': model.value,
        timestamp,
        'onUpdate:modelValue': (value: BalanceSnapshotPayloadAndLocation) => {
          model.value = value;
        },
      },
    });
  }

  it('should pre-populate fields from the v-model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    expect(amountInput.element.value).toBe('1.5');

    const assetInput = wrapper.find<HTMLInputElement>('[data-cy=asset] input');
    expect(assetInput.element.value).toBe('ETH');
  });

  it('should fail validation when category is missing', async () => {
    const model = baseModel();
    // @ts-expect-error category is required by type but we simulate invalid state
    model.category = undefined;
    wrapper = createWrapper(model);
    await vi.advanceTimersToNextTimerAsync();

    const valid = await wrapper.vm.validate();
    expect(valid).toBe(false);
  });

  it('should pass validation when category is set', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const valid = await wrapper.vm.validate();
    expect(valid).toBe(true);
  });

  it('should forward update:asset emitted by the inner price form', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const priceForm = wrapper.findComponent(EditBalancesSnapshotAssetPriceForm);
    expect(priceForm.exists()).toBe(true);

    priceForm.vm.$emit('update:asset', 'BTC');

    expect(wrapper.emitted('update:asset')).toBeTruthy();
    expect(wrapper.emitted('update:asset')?.[0]).toEqual(['BTC']);
  });

  it('should propagate amount edits through v-model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=amount] input').setValue('5');
    await vi.advanceTimersToNextTimerAsync();

    const updates = wrapper.emitted<[BalanceSnapshotPayloadAndLocation]>('update:modelValue');
    expect(updates).toBeTruthy();
    const last = updates!.at(-1)![0];
    expect(last.amount).toBe('5');
    expect(last.assetIdentifier).toBe('ETH');
  });

  it('should expose submitPrice without throwing', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(typeof wrapper.vm.submitPrice).toBe('function');
    expect(() => wrapper.vm.submitPrice()).not.toThrow();
  });

  it('should force amount to 1 when the model carries an NFT identifier', async () => {
    vi.useRealTimers();
    const model = baseModel();
    model.assetIdentifier = '_nft_0xabc/123';
    model.amount = '42';
    wrapper = createWrapper(model);
    await flushPromises();
    await nextTick();

    const updates = wrapper.emitted<[BalanceSnapshotPayloadAndLocation]>('update:modelValue');
    const nftUpdate = updates?.find(([payload]) => payload.amount === '1');
    expect(nftUpdate).toBeDefined();
    expect(nftUpdate?.[0].assetIdentifier).toBe('_nft_0xabc/123');
  });
});
