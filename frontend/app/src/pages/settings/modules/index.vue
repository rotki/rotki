<script setup lang="ts">
import ModuleSelector from '@/components/defi/wizard/ModuleSelector.vue';
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { SettingsHighlightIds } from '@/composables/settings/types';
import { NoteLocation } from '@/modules/common/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_MODULES,
  },
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsPage>
    <SettingCategory
      :id="SettingsHighlightIds.MODULES"
      class="mt-4"
    >
      <template #title>
        {{ t('module_settings.title') }}
      </template>
      <template #subtitle>
        {{ t('module_settings.subtitle') }}
      </template>
      <div class="flex flex-col gap-4 pt-4">
        <RuiAlert type="info">
          {{ t('module_settings.hint') }}
        </RuiAlert>
        <ModuleSelector />
      </div>
    </SettingCategory>
  </SettingsPage>
</template>
