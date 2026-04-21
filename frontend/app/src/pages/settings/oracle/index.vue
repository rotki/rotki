<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import OraclePenaltySettings from '@/modules/settings/data-security/oracle/OraclePenaltySettings.vue';
import PriceOracleSettings from '@/modules/settings/PriceOracleSettings.vue';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_ORACLE,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.PRICE_ORACLE, label: t('price_oracle_settings.title') },
  { id: SettingsCategoryIds.PENALTY, label: t('oracle_cache_management.penalty.title') },
]);
</script>

<template>
  <SettingsPage :navigation="navigation">
    <PriceOracleSettings :id="SettingsCategoryIds.PRICE_ORACLE" />
    <OraclePenaltySettings :id="SettingsCategoryIds.PENALTY" />
  </SettingsPage>
</template>
