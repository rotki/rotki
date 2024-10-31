<script setup lang="ts">
const { t } = useI18n();
const { evmchainsToSkipDetection } = storeToRefs(useGeneralSettingsStore());
const { evmChainsData, evmLikeChainsData } = useSupportedChains();
const chains = computed(() => [...get(evmChainsData), ...get(evmLikeChainsData)]);

const allSelected = computed(() => get(evmchainsToSkipDetection).length === get(chains).length);
const noneSelected = computed(() => get(evmchainsToSkipDetection).length === 0);

function selectAll(updateImmediate: (value: string[]) => void) {
  const allChainIds = get(chains).map(chain => chain.id);
  updateImmediate(allChainIds);
}

function deselectAll(updateImmediate: (value: string[]) => void) {
  updateImmediate([]);
}
</script>

<template>
  <div>
    <div class="text-rui-text-secondary text-body-1 mb-3">
      {{ t('general_settings.labels.chains_to_skip_detection') }}
    </div>
    <SettingsOption
      #default="{ error, success, updateImmediate, loading }"
      setting="evmchainsToSkipDetection"
      :error-message="t('general_settings.validation.chains_to_skip_detection.error')"
      :success-message="t('general_settings.validation.chains_to_skip_detection.success')"
    >
      <div class="flex flex-col gap-2">
        <div class="flex gap-2 pb-2">
          <RuiButton
            variant="text"
            size="sm"
            :disabled="loading || allSelected"
            @click="selectAll(updateImmediate)"
          >
            {{ t('general_settings.evm_chains.select') }}
          </RuiButton>
          <RuiButton
            variant="text"
            size="sm"
            :disabled="loading || noneSelected"
            @click="deselectAll(updateImmediate)"
          >
            {{ t('general_settings.evm_chains.deselect') }}
          </RuiButton>
        </div>
        <RuiAutoComplete
          :disabled="loading"
          :options="chains"
          :label="t('account_form.labels.blockchain', 2)"
          :model-value="evmchainsToSkipDetection"
          :success-messages="success"
          :error-messages="error"
          class="general-settings__fields__account-chains-to-skip-detection"
          data-cy="account-chain-skip-detection-field"
          variant="outlined"
          key-attr="id"
          text-attr="name"
          chips
          :item-height="56"
          auto-select-first
          @update:model-value="updateImmediate($event)"
        >
          <template #selection="{ item }">
            <ChainDisplay
              dense
              :chain="item.id"
            />
          </template>
          <template #item="{ item }">
            <ChainDisplay
              dense
              :chain="item.id"
            />
          </template>
        </RuiAutoComplete>
      </div>
    </SettingsOption>
  </div>
</template>
