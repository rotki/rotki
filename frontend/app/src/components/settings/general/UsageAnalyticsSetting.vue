<template>
  <settings-option
    #default="{ error, success, update }"
    setting="submitUsageAnalytics"
    :error-message="$tc('general_settings.validation.analytics.error')"
  >
    <v-switch
      v-model="anonymousUsageAnalytics"
      class="general-settings__fields__anonymous-usage-statistics mb-4 mt-0"
      color="primary"
      :label="$t('general_settings.labels.anonymous_analytics')"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';

const anonymousUsageAnalytics = ref<boolean>(false);
const { generalSettings } = useSettings();

onMounted(() => {
  const settings = get(generalSettings);
  set(anonymousUsageAnalytics, settings.submitUsageAnalytics);
});
</script>
