<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const autoCreateProfitEvents = ref<boolean>(false);
const { autoCreateProfitEvents: storedAutoCreateProfitEvents } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(autoCreateProfitEvents, get(storedAutoCreateProfitEvents));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    setting="autoCreateProfitEvents"
    :error-message="t('general_settings.history_event.auto_create_profit_events.validation.error')"
  >
    <template #title>
      {{ t('general_settings.history_event.auto_create_profit_events.title') }}
    </template>
    <template #default="{ error, success, updateImmediate }">
      <RuiSwitch
        v-model="autoCreateProfitEvents"
        color="primary"
        :label="t('general_settings.history_event.auto_create_profit_events.label')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </template>
  </SettingsOption>
</template>
