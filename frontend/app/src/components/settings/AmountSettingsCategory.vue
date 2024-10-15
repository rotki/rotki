<script setup lang="ts">
const { t } = useI18n();

const amountExample = bigNumberify(123456.789);
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.amount.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.amount.subtitle') }}
    </template>

    <SettingsItem>
      <template #title>
        {{ t('general_settings.version_update_check.title') }}
      </template>
      <MainCurrencySetting class="mb-4" />
      <div class="grid sm:grid-cols-3 gap-4">
        <FloatingPrecisionSetting />
        <NumericSeparatorsSettings />
      </div>
      <div class="flex gap-2 items-center">
        <div class="text-rui-text-secondary">
          {{ t('general_settings.amount.label.resulting_format') }}
        </div>
        <AmountDisplay
          :value="amountExample"
          show-currency="symbol"
        />
      </div>
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('general_settings.amount.label.abbreviation') }}
      </template>
      <AbbreviateNumberSetting />
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('general_settings.amount.label.currency_location') }}
      </template>
      <CurrencyLocationSetting />
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('rounding_settings.title') }}
      </template>
      <template #subtitle>
        {{ t('rounding_settings.subtitle') }}
      </template>
      <RoundingSettings />
    </SettingsItem>
  </SettingCategory>
</template>
