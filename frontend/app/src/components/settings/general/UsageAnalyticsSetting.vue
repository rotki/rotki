<script setup lang="ts">
const anonymousUsageAnalytics = ref<boolean>(false);
const { submitUsageAnalytics } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(anonymousUsageAnalytics, get(submitUsageAnalytics));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="submitUsageAnalytics"
    :error-message="t('general_settings.validation.analytics.error')"
  >
    <RuiSwitch
      v-model="anonymousUsageAnalytics"
      class="general-settings__fields__anonymous-usage-statistics"
      color="primary"
      :label="t('general_settings.labels.anonymous_analytics')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
