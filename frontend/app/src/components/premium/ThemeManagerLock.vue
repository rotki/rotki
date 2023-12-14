<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div class="theme-manager">
    <RuiCardHeader class="p-0">
      <template #header>
        {{ t('theme_manager_lock.title') }}
      </template>
      <template #subheader>
        {{ t('theme_manager_lock.subtitle') }}
      </template>
    </RuiCardHeader>

    <RuiCard dense class="mt-4">
      <div class="flex items-center gap-2 text-body-2">
        <PremiumLock />
        {{ t('theme_manager_lock.description') }}
      </div>
    </RuiCard>
  </div>
</template>
