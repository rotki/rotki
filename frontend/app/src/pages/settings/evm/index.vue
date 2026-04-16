<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingsPage from '@/modules/settings/controls/SettingsPage.vue';
import IndexerOrderSetting from '@/modules/settings/evm/IndexerOrderSetting.vue';
import EvmChainsToIgnoreSettings from '@/modules/settings/general/EvmChainsToIgnoreSettings.vue';
import TreatEthAsEth2Setting from '@/modules/settings/general/TreatEthAsEth2Setting.vue';
import { SettingsCategoryIds, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_EVM,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.CHAINS, label: t('evm_settings.general.title') },
  { id: SettingsCategoryIds.INDEXER, label: t('evm_settings.indexer.title') },
]);
</script>

<template>
  <SettingsPage
    class="evm-settings"
    :navigation="navigation"
  >
    <SettingCategory :id="SettingsCategoryIds.CHAINS">
      <template #title>
        {{ t('evm_settings.general.title') }}
      </template>
      <SettingsItem :id="SettingsHighlightIds.TREAT_ETH2_AS_ETH">
        <template #title>
          {{ t('evm_settings.general.treat_eth2_as_eth.title') }}
        </template>
        <template #subtitle>
          {{ t('evm_settings.general.treat_eth2_as_eth.subtitle') }}
        </template>
        <TreatEthAsEth2Setting />
      </SettingsItem>
      <SettingsItem :id="SettingsHighlightIds.CHAINS_TO_SKIP_DETECTION">
        <template #title>
          {{ t('evm_settings.general.chains_to_skip_detection.title') }}
        </template>
        <template #subtitle>
          {{ t('evm_settings.general.chains_to_skip_detection.subtitle') }}
        </template>
        <EvmChainsToIgnoreSettings />
      </SettingsItem>
    </SettingCategory>
    <IndexerOrderSetting :id="SettingsCategoryIds.INDEXER" />
  </SettingsPage>
</template>
