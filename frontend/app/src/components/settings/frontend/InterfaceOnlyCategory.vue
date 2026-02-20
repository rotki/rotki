<script setup lang="ts">
import Explorers from '@/components/settings/explorers/Explorers.vue';
import AnimationsEnabledSetting from '@/components/settings/frontend/AnimationsEnabledSetting.vue';
import PersistPrivacySettings from '@/components/settings/frontend/PersistPrivacySettings.vue';
import PersistTableSortingSetting from '@/components/settings/frontend/PersistTableSortingSetting.vue';
import ScrambleDataSetting from '@/components/settings/frontend/ScrambleDataSetting.vue';
import LanguageSetting from '@/components/settings/general/language/LanguageSetting.vue';
import QueryPeriodSetting from '@/components/settings/general/QueryPeriodSetting.vue';
import RefreshSetting from '@/components/settings/general/RefreshSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { SettingsHighlightIds } from '@/composables/settings/types';
import HistoryQueryIndicatorSettings from '@/modules/settings/interface/HistoryQueryIndicatorSettings.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.title') }}
    </template>
    <LanguageSetting />
    <AnimationsEnabledSetting :id="SettingsHighlightIds.ANIMATIONS" />
    <PersistTableSortingSetting :id="SettingsHighlightIds.PERSIST_TABLE_SORTING" />
    <ScrambleDataSetting :id="SettingsHighlightIds.SCRAMBLE" />
    <PersistPrivacySettings :id="SettingsHighlightIds.PERSIST_PRIVACY" />
    <RefreshSetting :id="SettingsHighlightIds.REFRESH_BALANCE" />
    <QueryPeriodSetting :id="SettingsHighlightIds.PERIODIC_QUERY" />
    <Explorers :id="SettingsHighlightIds.EXPLORERS" />
    <HistoryQueryIndicatorSettings />
  </SettingCategory>
</template>
