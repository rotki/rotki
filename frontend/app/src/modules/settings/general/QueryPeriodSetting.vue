<script setup lang="ts">
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';

const { t } = useI18n({ useScope: 'global' });

const { restart } = useMonitorService();
</script>

<template>
  <SettingNumber
    setting="queryPeriod"
    :label="t('frontend_settings.periodic_query.label')"
    :hint="t('frontend_settings.periodic_query.hint')"
    :min="5"
    :max="3600"
    :error-message="t('frontend_settings.periodic_query.validation.error')"
    @updated="restart()"
  />
</template>
