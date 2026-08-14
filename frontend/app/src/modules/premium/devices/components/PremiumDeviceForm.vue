<script setup lang="ts">
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { PremiumDevice } from '@/modules/premium/devices/premium';
import { useModelForm } from '@/modules/core/form/use-model-form';
import { deviceNameSchema, type DeviceNameState } from '@/modules/premium/devices/device-form-schema';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const modelValue = defineModel<string>({ required: true });

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false });

const { device } = defineProps<{
  device: PremiumDevice;
}>();

const { t } = useI18n({ useScope: 'global' });

// Read once, so the rule keeps comparing against the name the device had when the dialog opened.
const currentName = device.deviceName;

const schema = deviceNameSchema(currentName, {
  notEqual: t('premium_devices.form.device_name.error.not_equal'),
  required: t('premium_devices.form.device_name.error.required'),
});

// The dialog owns the name as a bare string, while the form core works on a state object, so the
// two are bridged here rather than by a pair of hand-written watchers.
const model = computed<DeviceNameState>({
  get: (): DeviceNameState => ({ deviceName: get(modelValue) }),
  set: (value: DeviceNameState): void => {
    set(modelValue, value.deviceName);
  },
});

const form = useModelForm<DeviceNameState>({
  model,
  schema,
  serverErrors: errors,
  stateUpdated,
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="mt-4">
    <RuiTextField
      v-model="form.state.deviceName"
      variant="outlined"
      color="primary"
      :label="t('premium_devices.form.device_name.label')"
      :hint="t('premium_devices.form.device_name.hint')"
      :error-messages="form.errors('deviceName')"
      data-testid="premium-device-name"
      @blur="form.touch('deviceName')"
    />

    <div>
      <div class="font-bold my-4">
        {{ t('premium_devices.form.info.title') }}
      </div>

      <RuiCard
        outlined
        no-padding
      >
        <div class="mx-4 py-4 border-b border-default">
          <div class="flex gap-4 items-center">
            <span class="font-medium w-[9rem]">
              {{ t('premium_devices.form.info.user') }}
            </span>
            <span class="flex-1 text-rui-text-secondary overflow-hidden flex items-center gap-2">
              {{ device.user }}
            </span>
          </div>
        </div>
        <div class="mx-4 py-4 border-b border-default">
          <div class="flex gap-4 items-center">
            <span class="font-medium w-[9rem]">
              {{ t('premium_devices.form.info.platform') }}
            </span>
            <span class="flex-1 text-rui-text-secondary overflow-hidden flex items-center gap-2">
              {{ device.platform }}
            </span>
          </div>
        </div>
        <div class="mx-4 py-4">
          <div class="flex gap-4 items-center">
            <span class="font-medium w-[9rem]">
              {{ t('premium_devices.form.info.last_seen') }}
            </span>
            <span class="flex-1 text-rui-text-secondary overflow-hidden flex items-center gap-2">
              <DateDisplay
                :timestamp="device.lastSeenAt"
                class="font-medium"
              />
            </span>
          </div>
        </div>
      </RuiCard>
    </div>
  </div>
</template>
