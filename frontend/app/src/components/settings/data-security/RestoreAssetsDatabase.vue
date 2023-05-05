<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
const { t } = useI18n();
</script>

<template>
  <fragment>
    <card class="mt-8">
      <template #title>{{ t('asset_update.restore.title') }}</template>
      <template #subtitle>{{ t('asset_update.restore.subtitle') }}</template>
      <restore-asset-db-button />
    </card>
  </fragment>
</template>
