<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import AskUserUponSizeDiscrepancySetting from '@/components/settings/general/AskUserUponSizeDiscrepancySetting.vue';
import AutoDetectTokensSetting from '@/components/settings/general/AutoDetectTokensSetting.vue';
import BalanceSaveFrequencySetting from '@/components/settings/general/BalanceSaveFrequencySetting.vue';
import BtcDerivationGapLimitSetting from '@/components/settings/general/BtcDerivationGapLimitSetting.vue';
import CsvExportDelimiterSetting from '@/components/settings/general/CsvExportDelimiterSetting.vue';
import DateDisplayFormatSetting from '@/components/settings/general/DateDisplayFormatSetting.vue';
import DateInputFormatSetting from '@/components/settings/general/DateInputFormatSetting.vue';
import DisplayDateInLocaltimeSetting from '@/components/settings/general/DisplayDateInLocaltimeSetting.vue';
import EventsProcessingFrequencySetting from '@/components/settings/general/EventsProcessingFrequencySetting.vue';
import UsageAnalyticsSetting from '@/components/settings/general/UsageAnalyticsSetting.vue';
import VersionUpdateFrequencySetting from '@/components/settings/general/VersionUpdateFrequencySetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.subtitle') }}
    </template>
    <UsageAnalyticsSetting />
    <AutoDetectTokensSetting />
    <SettingsItem>
      <template #title>
        {{ t('general_settings.display_date_in_localtime.title') }}
      </template>
      <div class="flex flex-col gap-2">
        <DisplayDateInLocaltimeSetting />
        <CsvExportDelimiterSetting />
      </div>
    </SettingsItem>
    <AskUserUponSizeDiscrepancySetting />
    <VersionUpdateFrequencySetting />
    <BalanceSaveFrequencySetting />
    <EventsProcessingFrequencySetting />
    <BtcDerivationGapLimitSetting />
    <SettingsItem>
      <template #title>
        {{ t('date_format_help.title') }}
      </template>
      <DateDisplayFormatSetting />
      <DateInputFormatSetting />
    </SettingsItem>
  </SettingCategory>
</template>
