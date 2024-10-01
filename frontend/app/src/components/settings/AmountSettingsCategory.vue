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

    <MainCurrencySetting class="mb-4" />
    <div class="grid sm:grid-cols-3 gap-4">
      <FloatingPrecisionSetting />
      <NumericSeparatorsSettings />
    </div>
    <AbbreviateNumberSetting />
    <CurrencyLocationSetting />

    <div>
      <strong>
        {{ t('general_settings.amount.label.resulting_format') }}
      </strong>
      <AmountDisplay
        :value="amountExample"
        show-currency="symbol"
      />
    </div>

    <RoundingSettings />
  </SettingCategory>
</template>
