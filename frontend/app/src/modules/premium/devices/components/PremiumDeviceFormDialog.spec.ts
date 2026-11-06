import type { PremiumDevice } from '@/modules/premium/devices/premium';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import PremiumDeviceFormDialog from '@/modules/premium/devices/components/PremiumDeviceFormDialog.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    updatePremiumDevice: vi.fn<(payload: { deviceIdentifier: string; deviceName: string }) => Promise<boolean>>(),
    validate: vi.fn<() => Promise<boolean>>(),
  },
}));

vi.mock('@/modules/premium/devices/devices', () => ({
  usePremiumDevicesApi: (): object => ({ updatePremiumDevice: spies.updatePremiumDevice }),
}));

const FormStub = defineComponent({
  name: 'PremiumDeviceForm',
  props: { errorMessages: { default: () => ({}), type: Object } },
  setup(_props, { expose }) {
    expose({ validate: spies.validate });
    return {};
  },
  template: '<div />',
});

const DEVICE: PremiumDevice = {
  deviceIdentifier: 'dev-1',
  deviceName: 'laptop',
  lastSeenAt: 1_760_000_000,
  platform: 'linux',
  user: 'alice',
};

function createWrapper(): VueWrapper<InstanceType<typeof PremiumDeviceFormDialog>> {
  return mount(PremiumDeviceFormDialog, {
    global: {
      stubs: {
        BigDialog: {
          emits: ['confirm', 'cancel'],
          props: ['display', 'failure', 'failureTitle', 'loading', 'title'],
          template: '<div v-if="display"><slot /></div>',
        },
        PremiumDeviceForm: FormStub,
      },
    },
    props: { modelValue: { ...DEVICE } },
  });
}

async function save(wrapper: VueWrapper): Promise<void> {
  wrapper.findComponent(BigDialog).vm.$emit('confirm');
  await flushPromises();
}

describe('premiumDeviceFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spies.validate.mockResolvedValue(true);
    spies.updatePremiumDevice.mockResolvedValue(true);
  });

  it('should close and ask for a reload once renamed', async () => {
    const wrapper = createWrapper();

    await save(wrapper);

    expect(spies.updatePremiumDevice).toHaveBeenCalledWith({ deviceIdentifier: 'dev-1', deviceName: 'laptop' });
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    expect(wrapper.emitted('refresh')).toHaveLength(1);
  });

  it('should stay open when the backend reports the rename did not happen', async () => {
    spies.updatePremiumDevice.mockResolvedValue(false);
    const wrapper = createWrapper();

    await save(wrapper);

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    expect(wrapper.emitted('refresh')).toBeUndefined();
  });

  it('should hand a field error back to the form', async () => {
    spies.updatePremiumDevice.mockRejectedValue(new ApiValidationError(JSON.stringify({ deviceName: ['taken'] })));
    const wrapper = createWrapper();

    await save(wrapper);

    expect(wrapper.findComponent(FormStub).props('errorMessages')).toEqual({ deviceName: ['taken'] });
    expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
  });

  it('should name any other failure in the dialog, which stays open', async () => {
    const error = new Error('server unreachable');
    spies.updatePremiumDevice.mockRejectedValue(error);
    const wrapper = createWrapper();

    await save(wrapper);

    expect(wrapper.findComponent(BigDialog).props('failure')).toBe(error);
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });
});
