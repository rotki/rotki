import { type BigNumber, bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, nextTick, ref } from 'vue';
import SnapshotFxOverrideControl from '@/modules/dashboard/snapshots/components/SnapshotFxOverrideControl.vue';

const setOverride = vi.fn(async (_value: BigNumber): Promise<boolean> => true);
const clearOverride = vi.fn(async (): Promise<boolean> => true);
const refreshOverride = vi.fn(async (): Promise<void> => {});

const isUsd = ref<boolean>(false);
const rate = ref<BigNumber>(bigNumberify(0.92));
const rateReady = ref<boolean>(true);
const loading = ref<boolean>(false);
const currentOverride = ref<BigNumber>();

vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-fx-override', () => ({
  useSnapshotFxOverride: (): Record<string, unknown> => ({
    clearOverride,
    currencySymbol: computed(() => 'EUR'),
    currentOverride,
    isUsd,
    loading,
    rate,
    rateReady,
    refreshOverride,
    saving: ref(false),
    setOverride,
  }),
}));

describe('modules/dashboard/snapshots/components/SnapshotFxOverrideControl', () => {
  let wrapper: VueWrapper<InstanceType<typeof SnapshotFxOverrideControl>>;

  function createWrapper(): VueWrapper<InstanceType<typeof SnapshotFxOverrideControl>> {
    return mount(SnapshotFxOverrideControl, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          AmountInput: { emits: ['update:modelValue'], props: ['modelValue'], template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)">' },
        },
      },
      props: { timestamp: 1_600_000_000 },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    set(isUsd, false);
    set(rateReady, true);
    set(loading, false);
    set(currentOverride, undefined);
    setOverride.mockClear();
    clearOverride.mockClear();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should render nothing when the display currency is USD', () => {
    set(isUsd, true);
    wrapper = createWrapper();

    expect(wrapper.find('[data-testid=snapshot-fx-override]').exists()).toBe(false);
  });

  it('should show the resolved rate when a historic rate is available', () => {
    wrapper = createWrapper();

    expect(wrapper.find('[data-testid=snapshot-fx-override-rate]').text()).toContain('0.92');
    expect(wrapper.find('[data-testid=snapshot-fx-override-manual]').exists()).toBe(false);
  });

  it('should flag a manually overridden rate', () => {
    set(currentOverride, bigNumberify(0.92));
    wrapper = createWrapper();

    expect(wrapper.find('[data-testid=snapshot-fx-override-manual]').exists()).toBe(true);
  });

  it('should show the dead-end warning and a set action when no rate resolves', () => {
    set(rateReady, false);
    wrapper = createWrapper();

    expect(wrapper.find('[data-testid=snapshot-fx-override-rate]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=snapshot-fx-override-set]').exists()).toBe(true);
  });

  it('should not show the dead-end warning while the rate lookup is loading', () => {
    set(rateReady, false);
    set(loading, true);
    wrapper = createWrapper();

    // The dead-end set action must wait until the lookup settles, not flash mid-load.
    expect(wrapper.find('[data-testid=snapshot-fx-override-set]').exists()).toBe(false);
  });

  it('should call setOverride with the entered rate on apply', async () => {
    wrapper = createWrapper();

    await wrapper.find('[data-testid=snapshot-fx-override-edit]').trigger('click');
    await wrapper.find('[data-testid=snapshot-fx-override-input]').setValue('0.88');
    await nextTick();
    await wrapper.find('[data-testid=snapshot-fx-override-apply]').trigger('click');

    expect(setOverride).toHaveBeenCalledTimes(1);
    expect(setOverride.mock.calls[0][0].toNumber()).toBe(0.88);
  });

  it('should call clearOverride from the clear action', async () => {
    set(currentOverride, bigNumberify(0.92));
    wrapper = createWrapper();

    await wrapper.find('[data-testid=snapshot-fx-override-edit]').trigger('click');
    await wrapper.find('[data-testid=snapshot-fx-override-clear]').trigger('click');

    expect(clearOverride).toHaveBeenCalledTimes(1);
  });
});
