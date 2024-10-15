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
    <SettingsItem>
      <template #title>
        {{ t('general_settings.display_date_in_localtime.title') }}
      </template>
      <div class="flex flex-col gap-2">
        <DisplayDateInLocaltimeSetting />
      </div>
    </SettingsItem>
    <AskUserUponSizeDiscrepancySetting />
    <VersionUpdateFrequencySetting />
    <BalanceSaveFrequencySetting />
    <SettingsItem>
      <template #title>
        {{ t('general_settings.labels.evm_chains') }}
      </template>
      <TreatEthAsEth2Setting />
      <EvmChainsToIgnoreSettings />
    </SettingsItem>
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
