<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import AmountSettingsCategory from '@/modules/settings/AmountSettingsCategory.vue';
import BackendServiceSettingsCategory from '@/modules/settings/BackendServiceSettingsCategory.vue';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import ExternalServiceSettingsCategory from '@/modules/settings/ExternalServiceSettingsCategory.vue';
import GeneralSettingsCategory from '@/modules/settings/GeneralSettingsCategory.vue';
import HistoryEventSettingsCategory from '@/modules/settings/HistoryEventSettingsCategory.vue';
import NftSettingsCategory from '@/modules/settings/NftSettingsCategory.vue';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_GENERAL,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.GENERAL, label: t('general_settings.title') },
  { id: SettingsCategoryIds.AMOUNT, label: t('general_settings.amount.title') },
  { id: SettingsCategoryIds.NFT, label: t('general_settings.nft_setting.title') },
  { id: SettingsCategoryIds.HISTORY_EVENT, label: t('general_settings.history_event.title') },
  { id: SettingsCategoryIds.EXTERNAL_SERVICE, label: t('general_settings.external_service_setting.title') },
  { id: SettingsCategoryIds.BACKEND, label: t('backend_settings.title') },
]);
</script>

<template>
  <SettingsPage
    class="general-settings"
    :navigation="navigation"
  >
    <GeneralSettingsCategory :id="SettingsCategoryIds.GENERAL" />
    <AmountSettingsCategory :id="SettingsCategoryIds.AMOUNT" />
    <NftSettingsCategory :id="SettingsCategoryIds.NFT" />
    <HistoryEventSettingsCategory :id="SettingsCategoryIds.HISTORY_EVENT" />
    <ExternalServiceSettingsCategory :id="SettingsCategoryIds.EXTERNAL_SERVICE" />
    <BackendServiceSettingsCategory :id="SettingsCategoryIds.BACKEND" />
  </SettingsPage>
</template>
