<script setup lang="ts">
const value = ref<boolean>(false);
const { autoDetectTokens } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(value, get(autoDetectTokens));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="autoDetectTokens"
    class="mb-4"
    :error-message="t('general_settings.validation.auto_detect_tokens.error')"
  >
    <RuiSwitch
      v-model="value"
      color="primary"
      :label="t('general_settings.labels.auto_detect_tokens')"
      :hint="t('general_settings.labels.auto_detect_tokens_hint')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
