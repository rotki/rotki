<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('asset_update.restore.title') }}
    </template>
    <template #subheader>
      {{ t('asset_update.restore.subtitle') }}
    </template>
    <template #footer>
      <RestoreAssetDbButton />
    </template>
  </RuiCard>
</template>
