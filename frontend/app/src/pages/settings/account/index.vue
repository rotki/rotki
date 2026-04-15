<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import ChangePassword from '@/components/settings/data-security/ChangePassword.vue';
import PasswordConfirmationSetting from '@/components/settings/data-security/PasswordConfirmationSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { SettingsCategoryIds, SettingsHighlightIds } from '@/composables/settings/types';
import { NoteLocation } from '@/modules/common/notes';

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
