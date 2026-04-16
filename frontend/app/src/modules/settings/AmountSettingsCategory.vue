<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AbbreviateNumberSetting from '@/modules/settings/general/amount/AbbreviateNumberSetting.vue';
import FloatingPrecisionSetting from '@/modules/settings/general/amount/FloatingPrecisionSetting.vue';
import MainCurrencySetting from '@/modules/settings/general/amount/MainCurrencySetting.vue';
import NumericSeparatorsSettings from '@/modules/settings/general/amount/NumericSeparatorsSettings.vue';
import RoundingSettings from '@/modules/settings/general/amount/RoundingSettings.vue';
import CurrencyLocationSetting from '@/modules/settings/general/CurrencyLocationSetting.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
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

    <SettingsItem :id="SettingsHighlightIds.AMOUNT_FORMAT">
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

    <SettingsItem :id="SettingsHighlightIds.SUBSCRIPT">
      <template #title>
        {{ t('rounding_settings.subscript.title') }}
      </template>
      <template #subtitle>
        {{ t('rounding_settings.subscript.subtitle') }}
      </template>
      <SubscriptToggle />
    </SettingsItem>

    <SettingsItem :id="SettingsHighlightIds.ROUNDING">
      <template #title>
        {{ t('rounding_settings.title') }}
      </template>
      <template #subtitle>
        {{ t('rounding_settings.subtitle') }}
      </template>
      <RoundingSettings />
    </SettingsItem>

    <SettingsItem :id="SettingsHighlightIds.ABBREVIATION">
      <template #title>
        {{ t('general_settings.amount.label.abbreviation') }}
      </template>
      <AbbreviateNumberSetting />
    </SettingsItem>

    <SettingsItem :id="SettingsHighlightIds.CURRENCY_LOCATION">
      <template #title>
        {{ t('general_settings.amount.label.currency_location') }}
      </template>
      <CurrencyLocationSetting />
    </SettingsItem>
  </SettingCategory>
</template>
