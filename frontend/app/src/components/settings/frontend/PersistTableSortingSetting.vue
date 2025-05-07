<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const persist = ref<boolean>(false);
const { t } = useI18n({ useScope: 'global' });

const { persistTableSorting: enabled } = storeToRefs(useFrontendSettingsStore());

watchImmediate(enabled, (enabled) => {
  set(persist, enabled);
});
</script>

<template>
  <SettingsOption
    setting="persistTableSorting"
    frontend-setting
    :error-message="t('frontend_settings.persist_table_sorting.validation.error')"
  >
    <template #title>
      {{ t('frontend_settings.persist_table_sorting.title') }}
    </template>
    <template #default="{ error, success, updateImmediate }">
      <RuiSwitch
        color="primary"
        :model-value="persist"
        :label="t('frontend_settings.persist_table_sorting.subtitle')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </template>
  </SettingsOption>
</template>
