<script setup lang="ts">
const animationsEnabled = ref<boolean>(true);
const { t } = useI18n();

const { animationsEnabled: enabled } = storeToRefs(useSessionSettingsStore());
const transform = (value: boolean) => !value;

onMounted(() => {
  set(animationsEnabled, get(enabled));
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="animationsEnabled"
    session-setting
    :transform="transform"
    :error-message="t('frontend_settings.validation.animations.error')"
  >
    <VSwitch
      :value="!animationsEnabled"
      class="general-settings__fields__animation-enabled mt-0"
      :label="t('frontend_settings.label.animations')"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </SettingsOption>
</template>
