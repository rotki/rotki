<script lang="ts" setup>
import { useAccountImportProgressStore } from '@/store/use-account-import-progress-store';

const { progress, progressPercentage } = storeToRefs(useAccountImportProgressStore());
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="!bg-black/[0.04] dark:!bg-white/[0.04] rounded-sm">
    <span class="text-body-2 p-2">
      {{ t('account_import_progress.importing', { current: progress.current, total: progress.total }) }}
    </span>
    <RuiProgress
      :value="progressPercentage"
      color="primary"
    />
  </div>
</template>
