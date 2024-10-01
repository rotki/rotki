<script setup lang="ts">
const { t } = useI18n();
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
    <DisplayDateInLocaltimeSetting />
    <AskUserUponSizeDiscrepancySetting />
    <VersionUpdateFrequencySetting />
    <BalanceSaveFrequencySetting />
    <DateDisplayFormatSetting />
    <DateInputFormatSetting />
    <CsvExportDelimiterSetting />
    <BtcDerivationGapLimitSetting />
    <TreatEthAsEth2Setting />
    <EvmChainsToIgnoreSettings />
  </SettingCategory>
</template>
