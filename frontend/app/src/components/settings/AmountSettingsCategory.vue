<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import AbbreviateNumberSetting from '@/components/settings/general/amount/AbbreviateNumberSetting.vue';
import FloatingPrecisionSetting from '@/components/settings/general/amount/FloatingPrecisionSetting.vue';
import MainCurrencySetting from '@/components/settings/general/amount/MainCurrencySetting.vue';
import NumericSeparatorsSettings from '@/components/settings/general/amount/NumericSeparatorsSettings.vue';
import RoundingSettings from '@/components/settings/general/amount/RoundingSettings.vue';
import CurrencyLocationSetting from '@/components/settings/general/CurrencyLocationSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import SubscriptToggle from './general/amount/SubscriptToggle.vue';

const { t } = useI18n({ useScope: 'global' });

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
        {{ t('general_settings.amount.label.amount') }}
      </template>
      <MainCurrencySetting />
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
        {{ t('rounding_settings.subscript.title') }}
      </template>
      <template #subtitle>
        {{ t('rounding_settings.subscript.subtitle') }}
      </template>
      <SubscriptToggle />
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
  </SettingCategory>
</template>
