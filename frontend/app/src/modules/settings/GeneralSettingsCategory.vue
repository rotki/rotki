<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AskUserUponSizeDiscrepancySetting from '@/modules/settings/general/AskUserUponSizeDiscrepancySetting.vue';
import AutoDetectTokensSetting from '@/modules/settings/general/AutoDetectTokensSetting.vue';
import BalanceSaveFrequencySetting from '@/modules/settings/general/BalanceSaveFrequencySetting.vue';
import BtcDerivationGapLimitSetting from '@/modules/settings/general/BtcDerivationGapLimitSetting.vue';
import CsvExportDelimiterSetting from '@/modules/settings/general/CsvExportDelimiterSetting.vue';
import DateDisplayFormatSetting from '@/modules/settings/general/DateDisplayFormatSetting.vue';
import DateInputFormatSetting from '@/modules/settings/general/DateInputFormatSetting.vue';
import DisplayDateInLocaltimeSetting from '@/modules/settings/general/DisplayDateInLocaltimeSetting.vue';
import UsageAnalyticsSetting from '@/modules/settings/general/UsageAnalyticsSetting.vue';
import VersionUpdateFrequencySetting from '@/modules/settings/general/VersionUpdateFrequencySetting.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

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
    <UsageAnalyticsSetting :id="SettingsHighlightIds.USAGE_ANALYTICS" />
    <AutoDetectTokensSetting :id="SettingsHighlightIds.AUTO_DETECT_TOKENS" />
    <SettingsItem :id="SettingsHighlightIds.DISPLAY_DATE_IN_LOCALTIME">
      <template #title>
        {{ t('general_settings.display_date_in_localtime.title') }}
      </template>
      <div class="flex flex-col gap-2">
        <DisplayDateInLocaltimeSetting />
        <CsvExportDelimiterSetting />
      </div>
    </SettingsItem>
    <AskUserUponSizeDiscrepancySetting :id="SettingsHighlightIds.ASK_SIZE_DISCREPANCY" />
    <VersionUpdateFrequencySetting :id="SettingsHighlightIds.VERSION_UPDATE_CHECK" />
    <BalanceSaveFrequencySetting :id="SettingsHighlightIds.BALANCE_SAVE_FREQUENCY" />
    <BtcDerivationGapLimitSetting :id="SettingsHighlightIds.BTC_DERIVATION_GAP" />
    <SettingsItem :id="SettingsHighlightIds.DATE_FORMAT">
      <template #title>
        {{ t('date_format_help.title') }}
      </template>
      <DateDisplayFormatSetting />
      <DateInputFormatSetting />
    </SettingsItem>
  </SettingCategory>
</template>
