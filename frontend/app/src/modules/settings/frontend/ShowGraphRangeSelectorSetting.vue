<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="showGraphRangeSelector"
    :label="t('frontend_settings.graph_basis.range_selector.label')"
  />
</template>
