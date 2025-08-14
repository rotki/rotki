<script setup lang="ts">
import type { PremiumDevice } from '@/modules/premium/devices/composables/premium';
import type { ValidationErrors } from '@/types/api/errors';
import useVuelidate from '@vuelidate/core';
import { helpers, not, required, sameAs } from '@vuelidate/validators';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useFormStateWatcher } from '@/composables/form';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<string>({ required: true });

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false });

const props = defineProps<{
  device: PremiumDevice;
}>();

const { t } = useI18n({ useScope: 'global' });

const rules = {
  deviceName: {
    notEqual: helpers.withMessage(t('premium_devices.form.device_name.error.not_equal'), not(sameAs(props.device.deviceName))),
    required: helpers.withMessage(t('premium_devices.form.device_name.error.required'), required),
  },
};

const v$ = useVuelidate(rules, { deviceName: modelValue }, { $autoDirty: true, $externalResults: errors });

useFormStateWatcher({ deviceName: modelValue }, stateUpdated);

defineExpose({
  validate: async () => await get(v$).$validate(),
});
</script>

<template>
  <div class="mt-4">
    <RuiTextField
      v-model="modelValue"
      variant="outlined"
      color="primary"
      :label="t('premium_devices.form.device_name.label')"
      :hint="t('premium_devices.form.device_name.hint')"
      :error-messages="toMessages(v$.deviceName)"
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
