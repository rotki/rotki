<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <RuiCard class="mt-8">
    <template #header>{{ t('asset_update.restore.title') }}</template>
    <template #subheader>{{ t('asset_update.restore.subtitle') }}</template>
    <RestoreAssetDbButton />
  </RuiCard>
</template>
