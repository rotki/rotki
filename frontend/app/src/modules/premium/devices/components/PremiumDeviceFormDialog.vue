<script setup lang="ts">
import type { PremiumDevice } from '@/modules/premium/devices/premium';
import { useTemplateRef } from 'vue';
import { useSaveFailure } from '@/modules/core/form/use-save-failure';
import PremiumDeviceForm from '@/modules/premium/devices/components/PremiumDeviceForm.vue';
import { usePremiumDevicesApi } from '@/modules/premium/devices/devices';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<PremiumDevice | undefined>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const newDeviceName = ref<string>('');
const loading = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);

const form = useTemplateRef<InstanceType<typeof PremiumDeviceForm>>('form');

const { updatePremiumDevice } = usePremiumDevicesApi();
const { capture, clear, failure, modelFieldErrors } = useSaveFailure();

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
    clear();
    success = await updatePremiumDevice(payload);
  }
  catch (error: unknown) {
    success = false;
    capture(error, payload);
  }
  finally {
    set(loading, false);
  }

  if (success) {
    set(modelValue, undefined);
    emit('refresh');
  }

  return success;
}

watchImmediate(modelValue, (value: PremiumDevice | undefined) => {
  clear();
  if (isDefined(value)) {
    set(newDeviceName, get(value, 'deviceName'));
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
    :action="{ primary: t('common.actions.save') }"
    :layout="{ autoHeight: true, divide: true, maxWidth: '560px' }"
    :prompt-on-close="stateUpdated"
    :failure="failure"
    :failure-title="t('premium_devices.form.error.title')"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <PremiumDeviceForm
      v-if="modelValue"
      ref="form"
      v-model="newDeviceName"
      v-model:error-messages="modelFieldErrors"
      v-model:state-updated="stateUpdated"
      :device="modelValue"
    />
  </BigDialog>
</template>
