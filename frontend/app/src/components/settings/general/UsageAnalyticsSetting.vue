<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const anonymousUsageAnalytics = ref<boolean>(false);
const { submitUsageAnalytics } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(anonymousUsageAnalytics, get(submitUsageAnalytics));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    setting="submitUsageAnalytics"
    :error-message="t('general_settings.usage_analytics.validation.error')"
  >
    <template #title>
      {{ t('general_settings.usage_analytics.title') }}
    </template>
    <template #default="{ error, success, updateImmediate }">
      <RuiSwitch
        v-model="anonymousUsageAnalytics"
        data-cy="anonymous-usage-statistics-input"
        color="primary"
        :label="t('general_settings.usage_analytics.label')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </template>
  </SettingsOption>
</template>
