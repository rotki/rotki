<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import ModuleSelector from '@/modules/settings/modules/ModuleSelector.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import { anchorId } from '@/modules/settings/settings-actions';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

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
          <i18n-t
            keypath="module_settings.coverage_note"
            tag="div"
            class="mt-2"
          >
            <template #link>
              <ExternalLink
                :url="externalLinks.integrations"
                :text="t('module_settings.integrations_link_label')"
              />
            </template>
          </i18n-t>
        </RuiAlert>
        <ModuleSelector />
      </div>
    </SettingCategory>
  </SettingsPage>
</template>
