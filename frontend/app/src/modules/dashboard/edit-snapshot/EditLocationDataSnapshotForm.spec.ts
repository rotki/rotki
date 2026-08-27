import type { LocationDataSnapshotPayload } from '@/modules/dashboard/snapshots';
import { settleFormDebounce } from '@test/utils/form-timing';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import EditLocationDataSnapshotForm from '@/modules/dashboard/edit-snapshot/EditLocationDataSnapshotForm.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const MESSAGE_ENTER_TRANSITION_MS = 700;

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

  it('should show no validation message before anything is edited', async () => {
    const model = baseModel();
    model.location = '';
    model.usdValue = '';
    wrapper = createWrapper(model);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=edit-location-location] .details').exists()).toBe(false);
    expect(wrapper.find('[data-testid=edit-location-value] .details .text-rui-error').exists()).toBe(false);
  });

  it('should reveal both required messages once validate runs', async () => {
    const model = baseModel();
    model.location = '';
    model.usdValue = '';
    wrapper = createWrapper(model);
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersByTimeAsync(MESSAGE_ENTER_TRANSITION_MS);
    await nextTick();

    expect(wrapper.find('[data-testid=edit-location-location] .details').text())
      .toBe('dashboard.snapshot.edit.dialog.location_data.rules.location');
    expect(wrapper.find('[data-testid=edit-location-value] .details .text-rui-error').text())
      .toBe('dashboard.snapshot.edit.dialog.location_data.rules.value');
  });

  it('should show the value message once the field is emptied and left', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const value = wrapper.find('[data-testid=edit-location-value] input');
    await value.setValue('');
    await value.trigger('blur');
    await vi.advanceTimersByTimeAsync(MESSAGE_ENTER_TRANSITION_MS);

    expect(wrapper.find('[data-testid=edit-location-value] .details .text-rui-error').text())
      .toBe('dashboard.snapshot.edit.dialog.location_data.rules.value');
  });

  it('should not flag stateUpdated before anything is edited, so an untouched dialog closes clean', async () => {
    wrapper = createWrapper();
    await settleFormDebounce();

    expect(wrapper.emitted('update:stateUpdated')?.flat() ?? []).not.toContain(true);
  });

  it('should flag stateUpdated once a field is edited', async () => {
    wrapper = createWrapper();
    await settleFormDebounce();

    await wrapper.find('[data-testid=edit-location-value] input').setValue('6000');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should emit update:modelValue when the value field changes', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const amount = wrapper.findComponent(AmountInput);
    amount.vm.$emit('update:modelValue', '6000');
    await vi.advanceTimersToNextTimerAsync();

    const updates = wrapper.emitted<[LocationDataSnapshotPayload]>('update:modelValue');
    expect(updates).toBeTruthy();
    const last = updates!.at(-1)![0];
    expect(last.usdValue).toBe('6000');
    expect(last.location).toBe('blockchain');
  });
});
