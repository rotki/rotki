<script setup lang="ts">
import type { Blockchain } from '@rotki/common/lib/blockchain';

const { t } = useI18n();
const css = useCssModule();
const { evmchainsToSkipDetection } = storeToRefs(useGeneralSettingsStore());

const { getChainName, evmChainsData, evmLikeChainsData } = useSupportedChains();

const chains = computed(() => [...get(evmChainsData), ...get(evmLikeChainsData)]);

const items = computed(() => get(chains).map(({ id }) => id));

function filter(chain: Blockchain, queryText: string) {
  const item = get(chains).find(blockchain => blockchain.id === chain);
  if (!item)
    return false;

  const query = queryText.toLocaleLowerCase();

  const nameIncludes = item.name.toLocaleLowerCase().includes(query);

  const idIncludes = item.id.toLocaleLowerCase().includes(query);

  return nameIncludes || idIncludes;
}

function removeChain(chain: Blockchain) {
  return get(evmchainsToSkipDetection).filter(c => c !== chain);
}
</script>

<template>
  <div>
    <div class="text-rui-text-secondary text-body-1 mb-3">
      {{ t('general_settings.labels.chains_to_skip_detection') }}
    </div>
    <SettingsOption
      #default="{ error, success, update, updateImmediate, loading }"
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
        :value="evmchainsToSkipDetection"
        :success-messages="success"
        :error-messages="error"
        :class="css['chain-select']"
        class="general-settings__fields__account-chains-to-skip-detection"
        chips
        small-chips
        deletable-chips
        multiple
        clearable
        data-cy="account-chain-skip-detection-field"
        outlined
        auto-select-first
        @input="update($event)"
      >
        <template #selection="{ item }">
          <RuiChip
            size="sm"
            variant="filled"
            closeable
            @click:close="updateImmediate(removeChain(item))"
          >
            <span class="flex gap-1 -ml-1">
              <ChainIcon
                :chain="item"
                size="0.875rem"
              />
              {{ getChainName(item).value }}
            </span>
          </RuiChip>
        </template>
        <template #item="{ item }">
          <ChainDisplay
            :chain="item"
            dense
          />
        </template>
      </VAutocomplete>
    </SettingsOption>
  </div>
</template>

<style lang="scss" module>
/* stylelint-disable selector-class-pattern,selector-nested-pattern */

.chain-select {
  :global(.v-select__selections) {
    @apply gap-3;
  }
}
</style>
