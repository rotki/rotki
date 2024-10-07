<script setup lang="ts">
const { t } = useI18n();
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
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('general_settings.amount.label.abbreviation') }}
      </template>
      <AbbreviateNumberSetting />
    </SettingsItem>

    <CurrencyLocationSetting />

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
