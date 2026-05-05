import type { LocationDataSnapshotPayload } from '@/modules/dashboard/snapshots';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import EditLocationDataSnapshotForm from '@/modules/dashboard/edit-snapshot/EditLocationDataSnapshotForm.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

type FormInstance = InstanceType<typeof EditLocationDataSnapshotForm>;

describe('edit-snapshot/EditLocationDataSnapshotForm.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<FormInstance>;

  const baseModel = (): LocationDataSnapshotPayload => ({
    location: 'blockchain',
    timestamp: 1700000000,
    usdValue: '5000',
  });

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(modelValue: LocationDataSnapshotPayload = baseModel()): VueWrapper<FormInstance> {
    return mount(EditLocationDataSnapshotForm, {
      global: {
        plugins: [pinia],
      },
      props: {
        modelValue,
      },
    });
  }

  it('should pre-populate value from the v-model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const amount = wrapper.findComponent(AmountInput);
    expect(amount.props('modelValue')).toBe('5000');
  });

  it('should pass validation with valid model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const valid = await wrapper.vm.validate();
    expect(valid).toBe(true);
  });

  it('should fail validation when location is missing', async () => {
    const model = baseModel();
    model.location = '';
    wrapper = createWrapper(model);
    await vi.advanceTimersToNextTimerAsync();

    const valid = await wrapper.vm.validate();
    expect(valid).toBe(false);
  });

  it('should fail validation when usdValue is missing', async () => {
    const model = baseModel();
    model.usdValue = '';
    wrapper = createWrapper(model);
    await vi.advanceTimersToNextTimerAsync();

    const valid = await wrapper.vm.validate();
    expect(valid).toBe(false);
  });

  it('should emit update:modelValue when the value field changes', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const amount = wrapper.findComponent(AmountInput);
    amount.vm.$emit('update:modelValue', '6000');
    await vi.advanceTimersToNextTimerAsync();

    const updates = wrapper.emitted<[LocationDataSnapshotPayload]>('update:modelValue');
    expect(updates).toBeTruthy();
    const last = updates![updates!.length - 1][0];
    expect(last.usdValue).toBe('6000');
    expect(last.location).toBe('blockchain');
  });
});
