<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('asset_update.restore.title') }}
    </template>
    <template #subtitle>
      {{ t('asset_update.restore.subtitle') }}
    </template>
    <div class="flex flex-col gap-4">
      <RuiAlert type="warning">
        {{ t('asset_update.restore.warning') }}
      </RuiAlert>
      <RestoreAssetDbButton />
    </div>
  </SettingsItem>
</template>
