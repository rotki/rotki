<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import ChangePassword from '@/components/settings/data-security/ChangePassword.vue';
import AutoLoginThreshold from '@/components/settings/data-security/AutoLoginThreshold.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { NoteLocation } from '@/types/notes';
import { useGeneralSettingsStore } from '@/store/settings/general';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.SETTINGS_ACCOUNT,
  },
});

const { t } = useI18n({ useScope: 'global' });
const generalStore = useGeneralSettingsStore();
const { autoLoginConfirmationThreshold: storeThreshold } = storeToRefs(generalStore);

// Local ref for two-way binding with the component
const localThreshold = ref(get(storeThreshold));

// Watch store changes to update local value
watch(storeThreshold, (newValue) => {
  set(localThreshold, newValue);
});

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
      
      <AutoLoginThreshold v-model:auto-login-confirmation-threshold="localThreshold" />
    </SettingCategory>
  </SettingsPage>
</template>
