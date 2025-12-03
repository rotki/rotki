<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import IndexerOrderSetting from '@/components/settings/evm/IndexerOrderSetting.vue';
import EvmChainsToIgnoreSettings from '@/components/settings/general/EvmChainsToIgnoreSettings.vue';
import TreatEthAsEth2Setting from '@/components/settings/general/TreatEthAsEth2Setting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_EVM,
  },
});

const { t } = useI18n({ useScope: 'global' });

enum Category {
  CHAINS = 'chains',
  INDEXER = 'indexer',
}

const navigation = [
  { id: Category.CHAINS, label: t('evm_settings.general.title') },
  { id: Category.INDEXER, label: t('evm_settings.indexer.title') },
];
</script>

<template>
  <SettingsPage
    class="evm-settings"
    :navigation="navigation"
  >
    <SettingCategory>
      <template #title>
        {{ t('evm_settings.general.title') }}
      </template>
      <SettingsItem>
        <template #title>
          {{ t('evm_settings.general.treat_eth2_as_eth.title') }}
        </template>
        <template #subtitle>
          {{ t('evm_settings.general.treat_eth2_as_eth.subtitle') }}
        </template>
        <TreatEthAsEth2Setting />
      </SettingsItem>
      <SettingsItem>
        <template #title>
          {{ t('evm_settings.general.chains_to_skip_detection.title') }}
        </template>
        <template #subtitle>
          {{ t('evm_settings.general.chains_to_skip_detection.subtitle') }}
        </template>
        <EvmChainsToIgnoreSettings />
      </SettingsItem>
    </SettingCategory>
    <IndexerOrderSetting :id="Category.INDEXER" />
  </SettingsPage>
</template>
