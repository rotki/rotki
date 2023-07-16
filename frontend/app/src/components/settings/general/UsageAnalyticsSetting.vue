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
    #default="{ error, success, update }"
    setting="submitUsageAnalytics"
    :error-message="t('general_settings.validation.analytics.error')"
  >
    <VSwitch
      v-model="anonymousUsageAnalytics"
      class="general-settings__fields__anonymous-usage-statistics mb-4 mt-0"
      color="primary"
      :label="t('general_settings.labels.anonymous_analytics')"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </SettingsOption>
</template>
