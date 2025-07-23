<script setup lang="ts">
import type { PremiumDevice } from '@/modules/premium/devices/composables/premium';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import PremiumDeviceForm from '@/modules/premium/devices/components/PremiumDeviceForm.vue';
import { usePremiumDevicesApi } from '@/modules/premium/devices/composables/devices';
import { useMessageStore } from '@/store/message';
import { ApiValidationError } from '@/types/api/errors';

const modelValue = defineModel<PremiumDevice | undefined>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const newDeviceName = ref<string>('');
const errorMessages = ref<Record<string, string[]>>({});
const loading = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);

const form = useTemplateRef<InstanceType<typeof PremiumDeviceForm>>('form');

const { updatePremiumDevice } = usePremiumDevicesApi();
const { setMessage } = useMessageStore();

async function save(): Promise<boolean> {
  const formRef = get(form);
  const valid = await formRef?.validate();
  const deviceName = get(newDeviceName);
  if (!valid || !isDefined(modelValue))
    return false;

  let success = false;
  set(loading, true);
  const { deviceIdentifier } = get(modelValue);
  const payload = { deviceIdentifier, deviceName };
  try {
    set(errorMessages, {});

    success = await updatePremiumDevice(payload);
    set(modelValue, undefined);
  }
  catch (error: any) {
    success = false;
    let errors = error.message;
    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(payload);

    if (typeof errors === 'object') {
      set(errorMessages, errors);
    }
    else {
      setMessage({
        description: errors || error,
        title: t('premium_devices.form.error.title'),
      });
    }
  }
  finally {
    set(loading, false);
  }

  if (success) {
    emit('refresh');
  }

  return success;
}

watchImmediate(modelValue, (modelValue) => {
  if (isDefined(modelValue)) {
    set(newDeviceName, get(modelValue, 'deviceName'));
  }
  else {
    set(newDeviceName, '');
  }
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="t('premium_devices.form.edit_title')"
    :loading="loading"
    :primary-action="t('common.actions.save')"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <PremiumDeviceForm
      v-if="modelValue"
      ref="form"
      v-model="newDeviceName"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :device="modelValue"
    />
  </BigDialog>
</template>
