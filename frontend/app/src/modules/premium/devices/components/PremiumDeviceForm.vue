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

/**
 * Bridges the dialog's bare string to the state object the form core works on, which is why this is
 * a writable computed rather than a pair of hand-written watchers.
 */
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
  <div class="flex flex-col gap-2">
    <dl
      class="grid grid-cols-3 gap-4 m-0 mb-4 rounded-rui-control border border-rui-divider px-4 py-3"
      data-testid="premium-device-summary"
    >
      <div class="flex flex-col gap-1 min-w-0">
        <dt class="text-sm font-medium text-rui-text-secondary">
          {{ t('premium_devices.form.info.user') }}
        </dt>
        <dd class="m-0 font-medium text-rui-text truncate">
          {{ device.user }}
        </dd>
      </div>
      <div class="flex flex-col gap-1 min-w-0">
        <dt class="text-sm font-medium text-rui-text-secondary">
          {{ t('premium_devices.form.info.platform') }}
        </dt>
        <dd class="m-0 font-medium text-rui-text truncate">
          {{ device.platform }}
        </dd>
      </div>
      <div class="flex flex-col gap-1">
        <dt class="text-sm font-medium text-rui-text-secondary">
          {{ t('premium_devices.form.info.last_seen') }}
        </dt>
        <dd class="m-0 text-rui-text">
          <DateDisplay :timestamp="device.lastSeenAt" />
        </dd>
      </div>
    </dl>
    <RuiTextField
      v-model="form.state.deviceName"
      color="primary"
      :label="t('premium_devices.form.device_name.label')"
      :hint="t('premium_devices.form.device_name.hint')"
      :error-messages="form.errors('deviceName')"
      data-testid="premium-device-name"
      @blur="form.touch('deviceName')"
    />
  </div>
</template>
