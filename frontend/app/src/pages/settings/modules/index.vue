<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import ModuleSelector from '@/modules/settings/modules/ModuleSelector.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import { anchorId } from '@/modules/settings/settings-actions';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.settings_sub.modules'), icon: 'lu-layout-grid', parent: '/settings' },
    noteLocation: NoteLocation.SETTINGS_MODULES,
  },
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsPage>
    <SettingCategory
      :id="anchorId('modules')"
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
