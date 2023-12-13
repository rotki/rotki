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
    <ModuleSelector class="mt-6" />
    <span class="text-caption" v-text="t('module_settings.hint')" />
  </RuiCard>
</template>
