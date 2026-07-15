<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AskUserUponSizeDiscrepancySetting from '@/modules/settings/general/AskUserUponSizeDiscrepancySetting.vue';
import AutoDetectTokensCooldownSetting from '@/modules/settings/general/AutoDetectTokensCooldownSetting.vue';
import AutoDetectTokensOnLoginSetting from '@/modules/settings/general/AutoDetectTokensOnLoginSetting.vue';
import AutoDetectTokensSetting from '@/modules/settings/general/AutoDetectTokensSetting.vue';
import BalanceSaveFrequencySetting from '@/modules/settings/general/BalanceSaveFrequencySetting.vue';
import BtcDerivationGapLimitSetting from '@/modules/settings/general/BtcDerivationGapLimitSetting.vue';
import CsvExportDelimiterSetting from '@/modules/settings/general/CsvExportDelimiterSetting.vue';
import DateDisplayFormatSetting from '@/modules/settings/general/DateDisplayFormatSetting.vue';
import DateInputFormatSetting from '@/modules/settings/general/DateInputFormatSetting.vue';
import DisabledChainQueriesSettings from '@/modules/settings/general/disabled-chain-queries/DisabledChainQueriesSettings.vue';
import DisplayDateInLocaltimeSetting from '@/modules/settings/general/DisplayDateInLocaltimeSetting.vue';
import UsageAnalyticsSetting from '@/modules/settings/general/UsageAnalyticsSetting.vue';
import VersionUpdateFrequencySetting from '@/modules/settings/general/VersionUpdateFrequencySetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import { useSetting } from '@/modules/settings/use-setting';

const { t } = useI18n({ useScope: 'global' });

const autoDetectTokensOnLogin = useSetting('autoDetectTokensOnLogin');
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.subtitle') }}
    </template>
    <SettingsItem setting-key="submitUsageAnalytics">
      <UsageAnalyticsSetting />
    </SettingsItem>
    <SettingsItem setting-key="autoDetectTokens">
      <AutoDetectTokensSetting />
    </SettingsItem>
    <SettingsItem setting-key="autoDetectTokensOnLogin">
      <template #subtitle>
        {{ t('general_settings.auto_detect_tokens_on_login.subtitle') }}
      </template>
      <AutoDetectTokensOnLoginSetting />
    </SettingsItem>
    <SettingsItem
      v-if="autoDetectTokensOnLogin"
      setting-key="autoDetectTokensCooldownHours"
    >
      <template #subtitle>
        {{ t('general_settings.auto_detect_tokens_cooldown.subtitle') }}
      </template>
      <AutoDetectTokensCooldownSetting />
    </SettingsItem>
    <SettingsItem setting-key="displayDateInLocaltime">
      <div class="flex flex-col gap-2">
        <DisplayDateInLocaltimeSetting />
        <CsvExportDelimiterSetting />
      </div>
    </SettingsItem>
    <AskUserUponSizeDiscrepancySetting />
    <VersionUpdateFrequencySetting />
    <SettingsItem setting-key="balanceSaveFrequency">
      <BalanceSaveFrequencySetting />
    </SettingsItem>
    <SettingsItem setting-key="btcDerivationGapLimit">
      <BtcDerivationGapLimitSetting />
    </SettingsItem>
    <SettingsItem setting-key="dateDisplayFormat">
      <DateDisplayFormatSetting />
      <DateInputFormatSetting />
    </SettingsItem>
    <SettingsItem setting-key="disabledChainQueries">
      <template #subtitle>
        {{ t('general_settings.disabled_chain_queries.subtitle') }}
      </template>
      <DisabledChainQueriesSettings />
    </SettingsItem>
  </SettingCategory>
</template>
