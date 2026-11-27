<script setup lang="ts">
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import DataIssuesTabs from '@/modules/history/data-issues/DataIssuesTabs.vue';

const { detecting = false, loading = false } = defineProps<{
  detecting?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  detect: [];
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <DataIssuesTabs />
  <RuiTooltip :open-delay="400">
    <template #activator>
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="detecting"
        data-testid="data-issues-detect"
        @click="emit('detect')"
      >
        <template #prepend>
          <RuiIcon name="lu-scale" />
        </template>
        {{ t('data_issues.detect.action') }}
      </RuiButton>
    </template>
    {{ t('data_issues.detect.tooltip') }}
  </RuiTooltip>

  <RuiTooltip :open-delay="400">
    <template #activator>
      <RuiButton
        variant="outlined"
        color="primary"
        :loading="loading"
        data-testid="data-issues-refresh"
        @click="emit('refresh')"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
    </template>
    {{ t('data_issues.refresh_tooltip') }}
  </RuiTooltip>
</template>
