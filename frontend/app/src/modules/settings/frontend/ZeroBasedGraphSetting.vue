<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="pb-2">
    <SettingSwitch
      setting="graphZeroBased"
      :label="t('frontend_settings.graph_basis.zero_based.label')"
      :hint="t('frontend_settings.graph_basis.zero_based.hint')"
    />
  </div>
</template>
