<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('module_settings.title') }}
    </template>
    <template #subheader>
      {{ t('module_settings.active_modules_description') }}
    </template>
    <ModuleSelector />
    <span class="text-caption text-rui-text-secondary">
      {{ t('module_settings.hint') }}
    </span>
  </RuiCard>
</template>
