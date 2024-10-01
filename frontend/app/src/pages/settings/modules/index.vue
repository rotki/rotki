<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_MODULES,
  },
});

const { t } = useI18n();
</script>

<template>
  <SettingsPage>
    <SettingCategory>
      <template #title>
        {{ t('module_settings.title') }}
      </template>
      <template #subtitle>
        {{ t('module_settings.active_modules_description') }}
      </template>
    </SettingCategory>
    <RuiAlert
      type="warning"
      class="mb-4"
    >
      {{ t('decentralized_overview.deprecated_warning') }}
    </RuiAlert>
    <ModuleSelector />
    <span class="text-caption text-rui-text-secondary">
      {{ t('module_settings.hint') }}
    </span>
  </SettingsPage>
</template>
