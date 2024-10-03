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
    <SettingItem>
      <VersionUpdateFrequencySetting />
      <BalanceSaveFrequencySetting />
    </SettingItem>
    <SettingItem>
      <TreatEthAsEth2Setting />
      <EvmChainsToIgnoreSettings />
    </SettingItem>
    <BtcDerivationGapLimitSetting />
    <DateDisplayFormatSetting />
    <DateInputFormatSetting />
    <CsvExportDelimiterSetting />      <!-- it should me moved -->
  </SettingCategory>
</template>
