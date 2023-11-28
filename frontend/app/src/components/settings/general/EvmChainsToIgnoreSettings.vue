<script setup lang="ts">
import { keyBy } from 'lodash-es';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Module } from '@/types/modules';

const { t } = useI18n();
const css = useCssModule();
const { isModuleEnabled } = useModules();
const { evmchainsToSkipDetection } = storeToRefs(useGeneralSettingsStore());

const { getEvmChainName, isEvm, evmChainsData, supportedChains } =
  useSupportedChains();

const skippedChains = computed(() => {
  const savedNames = get(evmchainsToSkipDetection) ?? [];
  const chainsData = get(evmChainsData) ?? [];
  const chainsMap = keyBy(chainsData, 'evmChainName');

  return savedNames.map(name => chainsMap[name]?.id);
});

const items = computed(() => {
  const isEth2Enabled = get(isModuleEnabled(Module.ETH2));

  let data: string[] = get(supportedChains).map(({ id }) => id);

  data = data.filter(symbol => get(isEvm(symbol as Blockchain)));

  if (!isEth2Enabled) {
    data = data.filter(symbol => symbol !== Blockchain.ETH2);
  }

  return data;
});

const getChainNames = (chains: Blockchain[]) =>
  (chains ?? []).map(getEvmChainName);

const filter = (chain: Blockchain, queryText: string) => {
  const item = get(supportedChains).find(blockchain => blockchain.id === chain);
  if (!item) {
    return false;
  }

  const nameIncludes = item.name
    .toLocaleLowerCase()
    .includes(queryText.toLocaleLowerCase());

  const idIncludes = item.id
    .toLocaleLowerCase()
    .includes(queryText.toLocaleLowerCase());

  return nameIncludes || idIncludes;
};
</script>

<template>
  <div>
    <div class="text-[1rem] mb-3 mt-4">
      {{ t('general_settings.labels.chains_to_skip_detection') }}
    </div>
    <SettingsOption
      #default="{ error, success, update, loading }"
      setting="evmchainsToSkipDetection"
      :error-message="
        t('general_settings.validation.chains_to_skip_detection.error')
      "
      :success-message="
        t('general_settings.validation.chains_to_skip_detection.success')
      "
    >
      <VAutocomplete
        :disabled="loading"
        :items="items"
        :filter="filter"
        :label="t('account_form.labels.blockchain', 2)"
        :value="skippedChains"
        :success-messages="success"
        :error-messages="error"
        :class="css['chain-select']"
        multiple
        clearable
        data-cy="account-chain-skip-detection-field"
        outlined
        auto-select-first
        @input="update(getChainNames($event))"
      >
        <template #selection="{ item }">
          <ChainDisplay :chain="item" :full-width="false" dense />
        </template>
        <template #item="{ item }">
          <ChainDisplay :chain="item" dense />
        </template>
      </VAutocomplete>
    </SettingsOption>
  </div>
</template>

<style lang="scss" module>
/* stylelint-disable selector-class-pattern,selector-nested-pattern */

.chain-select {
  :global(.v-select__selections) {
    @apply gap-4;
  }
}
</style>
