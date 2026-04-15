<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import OracleCacheManagement from '@/components/settings/data-security/oracle/OracleCacheManagement.vue';
import OraclePenaltySettings from '@/components/settings/data-security/oracle/OraclePenaltySettings.vue';
import PriceOracleSettings from '@/components/settings/PriceOracleSettings.vue';
import { SettingsCategoryIds } from '@/composables/settings/types';
import { NoteLocation } from '@/modules/common/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_ORACLE,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.PRICE_ORACLE, label: t('price_oracle_settings.title') },
  { id: SettingsCategoryIds.CACHE_MANAGEMENT, label: t('oracle_cache_management.title') },
  { id: SettingsCategoryIds.PENALTY, label: t('oracle_cache_management.penalty.title') },
]);
</script>

<template>
  <SettingsPage :navigation="navigation">
    <PriceOracleSettings :id="SettingsCategoryIds.PRICE_ORACLE" />
    <OracleCacheManagement :id="SettingsCategoryIds.CACHE_MANAGEMENT" />
    <OraclePenaltySettings :id="SettingsCategoryIds.PENALTY" />
  </SettingsPage>
</template>
