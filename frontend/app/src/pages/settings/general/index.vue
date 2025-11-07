<script setup lang="ts">
import AmountSettingsCategory from '@/components/settings/AmountSettingsCategory.vue';
import BackendServiceSettingsCategory from '@/components/settings/BackendServiceSettingsCategory.vue';
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import ExternalServiceSettingsCategory from '@/components/settings/ExternalServiceSettingsCategory.vue';
import GeneralSettingsCategory from '@/components/settings/GeneralSettingsCategory.vue';
import NftSettingsCategory from '@/components/settings/NftSettingsCategory.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_GENERAL,
  },
});

const { t } = useI18n({ useScope: 'global' });

enum Category {
  GENERAL = 'general',
  AMOUNT = 'amount',
  NFT = 'nft',
  EXTERNAL_SERVICE = 'external-service',
  BACKEND = 'backend',
}

const navigation = [
  { id: Category.GENERAL, label: t('general_settings.title') },
  { id: Category.AMOUNT, label: t('general_settings.amount.title') },
  { id: Category.NFT, label: t('general_settings.nft_setting.title') },
  { id: Category.EXTERNAL_SERVICE, label: t('general_settings.external_service_setting.title') },
  { id: Category.BACKEND, label: t('backend_settings.title') },
];
</script>

<template>
  <SettingsPage
    class="general-settings"
    :navigation="navigation"
  >
    <GeneralSettingsCategory :id="Category.GENERAL" />
    <AmountSettingsCategory :id="Category.AMOUNT" />
    <NftSettingsCategory :id="Category.NFT" />
    <ExternalServiceSettingsCategory :id="Category.EXTERNAL_SERVICE" />
    <BackendServiceSettingsCategory :id="Category.BACKEND" />
  </SettingsPage>
</template>

<style scoped lang="scss">
.general-settings {
  &__currency-list {
    font-size: 2em;
    font-weight: bold;
  }

  &__timeframe {
    min-height: 55px;
  }

  &__date-restore {
    margin-top: -6px;
  }
}
</style>
