<script setup lang="ts">
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
    #default="{ error, success, update }"
    setting="animationsEnabled"
    session-setting
    :transform="transform"
    :error-message="t('frontend_settings.validation.animations.error')"
  >
    <RuiSwitch
      color="primary"
      :model-value="!animationsEnabled"
      class="general-settings__fields__animation-enabled"
      :label="t('frontend_settings.label.animations')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="updateSetting($event, update)"
    />
  </SettingsOption>
</template>
