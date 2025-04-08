<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useSessionSettingsStore } from '@/store/settings/session';

const animationsEnabled = ref<boolean>(true);
const { t } = useI18n();

const { animationsEnabled: enabled } = storeToRefs(useSessionSettingsStore());
const transform = (value: boolean) => !value;

onMounted(() => {
  set(animationsEnabled, get(enabled));
});

function updateSetting(value: boolean, update: (newValue: any) => void) {
  set(animationsEnabled, !value);
  update(value);
}
</script>

<template>
  <SettingsOption
    setting="animationsEnabled"
    session-setting
    :transform="transform"
    :error-message="t('frontend_settings.animations.validation.error')"
  >
    <template #title>
      {{ t('frontend_settings.animations.title') }}
    </template>
    <template #default="{ error, success, updateImmediate }">
      <RuiSwitch
        color="primary"
        :model-value="!animationsEnabled"
        :label="t('frontend_settings.animations.animations_note')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateSetting($event, updateImmediate)"
      />
    </template>
  </SettingsOption>
</template>
