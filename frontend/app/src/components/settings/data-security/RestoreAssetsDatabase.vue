<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
const { t } = useI18n();
</script>

<template>
  <Fragment>
    <Card class="mt-8">
      <template #title>{{ t('asset_update.restore.title') }}</template>
      <template #subtitle>{{ t('asset_update.restore.subtitle') }}</template>
      <RestoreAssetDbButton />
    </Card>
  </Fragment>
</template>
