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
        {{ t('module_settings.subtitle') }}
      </template>
      <div class="flex flex-col gap-4 pt-4">
        <RuiAlert
          type="warning"
        >
          {{ t('decentralized_overview.deprecated_warning') }}
        </RuiAlert>
        <RuiAlert type="info">
          {{ t('module_settings.hint') }}
        </RuiAlert>
        <ModuleSelector />
      </div>
    </SettingCategory>
  </SettingsPage>
</template>
