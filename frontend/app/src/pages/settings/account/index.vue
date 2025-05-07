<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import ChangePassword from '@/components/settings/data-security/ChangePassword.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.SETTINGS_ACCOUNT,
  },
});

const { t } = useI18n({ useScope: 'global' });

enum Category {
  SECURITY = 'security',
}

const navigation = [
  { id: Category.SECURITY, label: t('settings.security_settings.title') },
];
</script>

<template>
  <SettingsPage :navigation="navigation">
    <SettingCategory :id="Category.SECURITY">
      <template #title>
        {{ t('settings.security_settings.title') }}
      </template>

      <template #subtitle>
        {{ t('settings.security_settings.subtitle') }}
      </template>

      <ChangePassword />
    </SettingCategory>
  </SettingsPage>
</template>
