<script setup lang="ts">
import { watchDebounced } from '@vueuse/core';
import { SettingLocation, useSettings } from '@/composables/settings';

const model = defineModel<number>('autoLoginConfirmationThreshold', { required: true });

const { t } = useI18n({ useScope: 'global' });
const { updateSetting } = useSettings();

const saving = ref(false);

async function saveThreshold(value: number) {
  set(saving, true);
  await updateSetting('autoLoginConfirmationThreshold', value, SettingLocation.GENERAL, {
    error: t('settings.security_settings.auto_login_confirmation_threshold.error'),
    success: '',
  });
  set(saving, false);
}

// Debounce the save to avoid calling API on every slider movement
watchDebounced(model, (value) => {
  saveThreshold(value);
}, { debounce: 500 });
</script>

<template>
  <SettingGroup>
    <template #title>
      {{ t('settings.security_settings.auto_login_confirmation_threshold.label') }}
    </template>

    <RuiSlider
      v-model="model"
      :min="3"
      :max="10"
      :step="1"
      :label="t('settings.security_settings.auto_login_confirmation_threshold.label')"
      :disabled="saving"
      show-thumb-label
      color="primary"
      class="mt-4"
    >
      <template #thumbLabel="{ modelValue }">
        {{ modelValue }}
      </template>
    </RuiSlider>

    <div class="text-rui-text-secondary text-caption mt-2">
      <template v-if="saving">
        <RuiProgress
          variant="indeterminate"
          thickness="2"
          size="16"
          color="primary"
          class="inline-block mr-2"
        />
        {{ t('settings.saving') }}
      </template>
      <template v-else>
        {{ t('settings.security_settings.auto_login_confirmation_threshold.description', { threshold: model }) }}
      </template>
    </div>
  </SettingGroup>
</template>
