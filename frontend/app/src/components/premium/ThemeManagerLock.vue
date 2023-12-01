<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div class="theme-manager">
    <div class="text-h6 mt-4">{{ t('theme_manager_lock.title') }}</div>
    <div class="text-subtitle-1">{{ t('theme_manager_lock.subtitle') }}</div>
    <RuiCard dense class="mt-4">
      <div class="flex items-center gap-2 text-body-2">
        <PremiumLock />
        {{ t('theme_manager_lock.description') }}
      </div>
    </RuiCard>
  </div>
</template>
