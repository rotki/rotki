<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
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
    <SettingsItem :id="SettingsHighlightIds.ANIMATIONS">
      <template #title>
        {{ t('frontend_settings.animations.title') }}
      </template>
      <AnimationsEnabledSetting />
    </SettingsItem>
    <SettingsItem :id="SettingsHighlightIds.PERSIST_TABLE_SORTING">
      <template #title>
        {{ t('frontend_settings.persist_table_sorting.title') }}
      </template>
      <PersistTableSortingSetting />
    </SettingsItem>
    <ScrambleDataSetting :id="SettingsHighlightIds.SCRAMBLE" />
    <SettingsItem :id="SettingsHighlightIds.PERSIST_PRIVACY">
      <template #title>
        {{ t('frontend_settings.persist_privacy.title') }}
      </template>
      <PersistPrivacySettings />
    </SettingsItem>
    <RefreshSetting :id="SettingsHighlightIds.REFRESH_BALANCE" />
    <SettingsItem :id="SettingsHighlightIds.PERIODIC_QUERY">
      <template #title>
        {{ t('frontend_settings.periodic_query.title') }}
      </template>
      <QueryPeriodSetting />
    </SettingsItem>
    <Explorers :id="SettingsHighlightIds.EXPLORERS" />
    <HistoryQueryIndicatorSettings />
  </SettingCategory>
</template>
