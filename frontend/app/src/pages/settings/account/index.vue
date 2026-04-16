<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import ChangePassword from '@/modules/settings/data-security/ChangePassword.vue';
import PasswordConfirmationSetting from '@/modules/settings/data-security/PasswordConfirmationSetting.vue';
import { SettingsCategoryIds, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.SETTINGS_ACCOUNT,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.SECURITY, label: t('settings.security_settings.title') },
]);
</script>

<template>
  <SettingsPage :navigation="navigation">
    <SettingCategory :id="SettingsCategoryIds.SECURITY">
      <template #title>
        {{ t('settings.security_settings.title') }}
      </template>

      <template #subtitle>
        {{ t('settings.security_settings.subtitle') }}
      </template>

      <ChangePassword />
      <PasswordConfirmationSetting :id="SettingsHighlightIds.PASSWORD_CONFIRMATION" />
    </SettingCategory>
  </SettingsPage>
</template>
