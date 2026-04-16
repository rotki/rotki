<script setup lang="ts">
import Explorers from '@/modules/settings/explorers/Explorers.vue';
import AnimationsEnabledSetting from '@/modules/settings/frontend/AnimationsEnabledSetting.vue';
import PersistPrivacySettings from '@/modules/settings/frontend/PersistPrivacySettings.vue';
import PersistTableSortingSetting from '@/modules/settings/frontend/PersistTableSortingSetting.vue';
import ScrambleDataSetting from '@/modules/settings/frontend/ScrambleDataSetting.vue';
import LanguageSetting from '@/modules/settings/general/language/LanguageSetting.vue';
import QueryPeriodSetting from '@/modules/settings/general/QueryPeriodSetting.vue';
import RefreshSetting from '@/modules/settings/general/RefreshSetting.vue';
import HistoryQueryIndicatorSettings from '@/modules/settings/interface/HistoryQueryIndicatorSettings.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

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
