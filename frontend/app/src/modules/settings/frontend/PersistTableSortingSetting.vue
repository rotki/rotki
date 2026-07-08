<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useSetting } from '@/modules/settings/use-setting';

const persist = ref<boolean>(false);
const { t } = useI18n({ useScope: 'global' });

const enabled = useSetting('persistTableSorting');

watchImmediate(enabled, (enabled) => {
  set(persist, enabled);
});
</script>

<template>
  <SettingsOption
    setting="persistTableSorting"
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
