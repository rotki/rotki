<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div class="theme-manager">
    <div class="text-h6 mt-4">{{ t('theme_manager_lock.title') }}</div>
    <div class="text-subtitle-1">{{ t('theme_manager_lock.subtitle') }}</div>
    <VSheet outlined rounded class="mt-4">
      <VRow align="center" class="py-3 px-2">
        <VCol cols="auto">
          <PremiumLock />
        </VCol>
        <VCol>{{ t('theme_manager_lock.description') }}</VCol>
      </VRow>
    </VSheet>
  </div>
</template>
