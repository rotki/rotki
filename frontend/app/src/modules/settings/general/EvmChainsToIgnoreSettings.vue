<script setup lang="ts">
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import SettingMultiSelect from '@/modules/settings/controls/SettingMultiSelect.vue';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { t } = useI18n({ useScope: 'global' });
const { evmChainsData, evmLikeChainsData } = useSupportedChains();

const chains = computed(() => [...get(evmChainsData), ...get(evmLikeChainsData)]);
</script>

<template>
  <SettingMultiSelect
    setting="evmchainsToSkipDetection"
    :options="chains"
    key-attr="id"
    text-attr="name"
    :bulk-actions="{
      clearLabel: t('general_settings.evm_chains.deselect'),
      selectLabel: t('general_settings.evm_chains.select'),
    }"
    :label="t('evm_settings.general.chains_to_skip_detection.label')"
    data-testid="chains-to-skip-detection"
    :item-height="56"
    :success-message="t('general_settings.validation.chains_to_skip_detection.success')"
    :error-message="t('general_settings.validation.chains_to_skip_detection.error')"
  >
    <template #selection.prepend="{ item }">
      <ChainIcon
        :chain="item.id"
        size="24px"
      />
    </template>
    <template #selection="{ item }">
      <span :data-value="item.id">{{ item.name }}</span>
    </template>
    <template #item="{ item }">
      <ChainDisplay
        :data-value="item.id"
        dense
        :chain="item.id"
      />
    </template>
  </SettingMultiSelect>
</template>
