<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AbbreviateNumberSetting from '@/modules/settings/general/amount/AbbreviateNumberSetting.vue';
import FloatingPrecisionSetting from '@/modules/settings/general/amount/FloatingPrecisionSetting.vue';
import MainCurrencySetting from '@/modules/settings/general/amount/MainCurrencySetting.vue';
import NumericSeparatorsSettings from '@/modules/settings/general/amount/NumericSeparatorsSettings.vue';
import RoundingSettings from '@/modules/settings/general/amount/RoundingSettings.vue';
import CsvExportDelimiterSetting from '@/modules/settings/general/CsvExportDelimiterSetting.vue';
import CurrencyLocationSetting from '@/modules/settings/general/CurrencyLocationSetting.vue';
import DateDisplayFormatSetting from '@/modules/settings/general/DateDisplayFormatSetting.vue';
import DateInputFormatSetting from '@/modules/settings/general/DateInputFormatSetting.vue';
import DisplayDateInLocaltimeSetting from '@/modules/settings/general/DisplayDateInLocaltimeSetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import SubscriptToggle from './general/amount/SubscriptToggle.vue';

const { t } = useI18n({ useScope: 'global' });

const amountExample = bigNumberify(123456.789);
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.formats.title') }}
    </template>

    <SettingsItem setting-key="currency">
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
        <FiatDisplay :value="amountExample" />
      </div>
    </SettingsItem>

    <SettingsItem setting-key="subscriptDecimals">
      <template #subtitle>
        {{ t('rounding_settings.subscript.subtitle') }}
      </template>
      <SubscriptToggle />
    </SettingsItem>

    <SettingsItem setting-key="amountRoundingMode">
      <template #title>
        {{ t('rounding_settings.title') }}
      </template>
      <template #subtitle>
        {{ t('rounding_settings.subtitle') }}
      </template>
      <RoundingSettings />
    </SettingsItem>

    <SettingsItem setting-key="abbreviateNumber">
      <template #title>
        {{ t('general_settings.amount.label.abbreviation') }}
      </template>
      <AbbreviateNumberSetting />
    </SettingsItem>

    <SettingsItem setting-key="currencyLocation">
      <CurrencyLocationSetting />
    </SettingsItem>

    <SettingsItem setting-key="dateDisplayFormat">
      <DateDisplayFormatSetting />
      <DateInputFormatSetting />
    </SettingsItem>

    <SettingsItem setting-key="displayDateInLocaltime">
      <div class="flex flex-col gap-2">
        <DisplayDateInLocaltimeSetting />
        <CsvExportDelimiterSetting />
      </div>
    </SettingsItem>
  </SettingCategory>
</template>
