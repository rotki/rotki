<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import OracleCacheManagement from '@/components/settings/data-security/oracle/OracleCacheManagement.vue';
import OraclePenaltySettings from '@/components/settings/data-security/oracle/OraclePenaltySettings.vue';
import PriceOracleSettings from '@/components/settings/PriceOracleSettings.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_ORACLE,
  },
});

const { t } = useI18n({ useScope: 'global' });

enum Category {
  PRICE_ORACLE = 'price-oracle',
  CACHE_MANAGEMENT = 'cache-management',
  PENALTY = 'penalty',
}

const navigation = [
  { id: Category.PRICE_ORACLE, label: t('price_oracle_settings.title') },
  { id: Category.CACHE_MANAGEMENT, label: t('oracle_cache_management.title') },
  { id: Category.PENALTY, label: t('oracle_cache_management.penalty.title') },
];
</script>

<template>
  <SettingsPage :navigation="navigation">
    <PriceOracleSettings :id="Category.PRICE_ORACLE" />
    <OracleCacheManagement :id="Category.CACHE_MANAGEMENT" />
    <OraclePenaltySettings :id="Category.PENALTY" />
  </SettingsPage>
</template>
