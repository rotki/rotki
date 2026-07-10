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
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
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
    <SettingsItem :id="SettingsHighlightIds.USAGE_ANALYTICS">
      <template #title>
        {{ t('general_settings.usage_analytics.title') }}
      </template>
      <UsageAnalyticsSetting />
    </SettingsItem>
    <SettingsItem :id="SettingsHighlightIds.AUTO_DETECT_TOKENS">
      <template #title>
        {{ t('general_settings.auto_detect_tokens.title') }}
      </template>
      <AutoDetectTokensSetting />
    </SettingsItem>
    <SettingsItem :id="SettingsHighlightIds.AUTO_DETECT_TOKENS_ON_LOGIN">
      <template #title>
        {{ t('general_settings.auto_detect_tokens_on_login.title') }}
      </template>
      <template #subtitle>
        {{ t('general_settings.auto_detect_tokens_on_login.subtitle') }}
      </template>
      <AutoDetectTokensOnLoginSetting />
    </SettingsItem>
    <SettingsItem
      v-if="autoDetectTokensOnLogin"
      :id="SettingsHighlightIds.AUTO_DETECT_TOKENS_COOLDOWN"
    >
      <template #title>
        {{ t('general_settings.auto_detect_tokens_cooldown.title') }}
      </template>
      <template #subtitle>
        {{ t('general_settings.auto_detect_tokens_cooldown.subtitle') }}
      </template>
      <AutoDetectTokensCooldownSetting />
    </SettingsItem>
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
    <SettingsItem :id="SettingsHighlightIds.BALANCE_SAVE_FREQUENCY">
      <template #title>
        {{ t('general_settings.balance_frequency.title') }}
      </template>
      <BalanceSaveFrequencySetting />
    </SettingsItem>
    <SettingsItem :id="SettingsHighlightIds.BTC_DERIVATION_GAP">
      <template #title>
        {{ t('general_settings.labels.btc_derivation_gap') }}
      </template>
      <BtcDerivationGapLimitSetting />
    </SettingsItem>
    <SettingsItem :id="SettingsHighlightIds.DATE_FORMAT">
      <template #title>
        {{ t('date_format_help.title') }}
      </template>
      <DateDisplayFormatSetting />
      <DateInputFormatSetting />
    </SettingsItem>
    <SettingsItem :id="SettingsHighlightIds.DISABLED_CHAIN_QUERIES">
      <template #title>
        {{ t('general_settings.disabled_chain_queries.title') }}
      </template>
      <template #subtitle>
        {{ t('general_settings.disabled_chain_queries.subtitle') }}
      </template>
      <DisabledChainQueriesSettings />
    </SettingsItem>
  </SettingCategory>
</template>
