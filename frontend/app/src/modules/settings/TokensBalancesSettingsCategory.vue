<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AutoDetectTokensCooldownSetting from '@/modules/settings/general/AutoDetectTokensCooldownSetting.vue';
import AutoDetectTokensOnLoginSetting from '@/modules/settings/general/AutoDetectTokensOnLoginSetting.vue';
import AutoDetectTokensSetting from '@/modules/settings/general/AutoDetectTokensSetting.vue';
import BalanceSaveFrequencySetting from '@/modules/settings/general/BalanceSaveFrequencySetting.vue';
import BtcDerivationGapLimitSetting from '@/modules/settings/general/BtcDerivationGapLimitSetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import { useSetting } from '@/modules/settings/use-setting';

const { t } = useI18n({ useScope: 'global' });

const autoDetectTokensOnLogin = useSetting('autoDetectTokensOnLogin');
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.tokens_balances.title') }}
    </template>
    <SettingsItem setting-key="autoDetectTokens">
      <AutoDetectTokensSetting />
    </SettingsItem>
    <SettingsItem setting-key="autoDetectTokensOnLogin">
      <template #subtitle>
        {{ t('general_settings.auto_detect_tokens_on_login.subtitle') }}
      </template>
      <AutoDetectTokensOnLoginSetting />
    </SettingsItem>
    <SettingsItem
      v-if="autoDetectTokensOnLogin"
      setting-key="autoDetectTokensCooldownHours"
    >
      <template #subtitle>
        {{ t('general_settings.auto_detect_tokens_cooldown.subtitle') }}
      </template>
      <AutoDetectTokensCooldownSetting />
    </SettingsItem>
    <SettingsItem setting-key="balanceSaveFrequency">
      <BalanceSaveFrequencySetting />
    </SettingsItem>
    <SettingsItem setting-key="btcDerivationGapLimit">
      <BtcDerivationGapLimitSetting />
    </SettingsItem>
  </SettingCategory>
</template>
