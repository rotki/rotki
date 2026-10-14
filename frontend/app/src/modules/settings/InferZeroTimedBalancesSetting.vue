<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import SettingsMenuSection from '@/modules/settings/SettingsMenuSection.vue';

const emit = defineEmits<{
  updated: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsMenuSection :title="t('statistics_graph_settings.infer_zero_timed_balances.title')">
    <SettingSwitch
      setting="inferZeroTimedBalances"
      size="sm"
      class="[&_span]:text-xs! [&_span]:text-rui-text-secondary"
      :debounce="1500"
      :label="t('statistics_graph_settings.infer_zero_timed_balances.label')"
      @updated="emit('updated')"
    />
  </SettingsMenuSection>
</template>
