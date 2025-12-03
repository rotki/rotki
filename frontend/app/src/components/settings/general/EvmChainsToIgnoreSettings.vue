<script setup lang="ts">
import ChainDisplay from '@/components/accounts/blockchain/ChainDisplay.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useGeneralSettingsStore } from '@/store/settings/general';

const { t } = useI18n({ useScope: 'global' });
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
            color="primary"
            :disabled="loading || allSelected"
            @click="selectAll(updateImmediate)"
          >
            {{ t('general_settings.evm_chains.select') }}
          </RuiButton>
          <RuiButton
            variant="text"
            size="sm"
            color="primary"
            :disabled="loading || noneSelected"
            @click="deselectAll(updateImmediate)"
          >
            {{ t('general_settings.evm_chains.deselect') }}
          </RuiButton>
        </div>
        <RuiAutoComplete
          :options="chains"
          :label="t('account_form.labels.blockchain', 2)"
          :model-value="evmchainsToSkipDetection"
          :success-messages="success"
          :error-messages="error"
          data-cy="chains-to-skip-detection"
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
              :data-value="item.id"
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
