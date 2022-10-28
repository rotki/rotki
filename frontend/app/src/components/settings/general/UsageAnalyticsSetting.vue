<template>
  <settings-option
    #default="{ error, success, update }"
    setting="submitUsageAnalytics"
    :error-message="tc('general_settings.validation.analytics.error')"
  >
    <v-switch
      v-model="anonymousUsageAnalytics"
      class="general-settings__fields__anonymous-usage-statistics mb-4 mt-0"
      color="primary"
      :label="tc('general_settings.labels.anonymous_analytics')"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { useGeneralSettingsStore } from '@/store/settings/general';

const anonymousUsageAnalytics = ref<boolean>(false);
const { submitUsageAnalytics } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(anonymousUsageAnalytics, get(submitUsageAnalytics));
});

const { tc } = useI18n();
</script>
