<script setup lang="ts">
import type { ChainInfo } from '@/modules/core/api/types/chains';
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import ChainAccountMultiSelect from '@/modules/accounts/ChainAccountMultiSelect.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import SettingsStatusMessage from '@/modules/settings/controls/SettingsStatusMessage.vue';
import {
  type DisabledChainQueries,
  useDisabledChainQueriesState,
} from '@/modules/settings/general/use-disabled-chain-queries-state';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const CHAIN_OPTION_HEIGHT_PX = 56;

const { t } = useI18n({ useScope: 'global' });

const { disabledChainQueries } = storeToRefs(useGeneralSettingsStore());
const { matchChain, supportedChains } = useSupportedChains();

const chains = computed<ChainInfo[]>(() => get(supportedChains));

const {
  excludedAddresses,
  isEntireChainDisabled,
  isTransientlyDisabled,
  selectChains,
  setEntireChainDisabled,
  setExcludedAddresses,
  visibleChainIds,
} = useDisabledChainQueriesState({
  matchChain,
  ready: (): boolean => get(supportedChains).length > 0,
  source: disabledChainQueries,
});

function commit(
  payload: DisabledChainQueries | undefined,
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  if (payload !== undefined)
    updateImmediate(payload);
}

function onChainsChange(
  newSelected: string[],
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  commit(selectChains(newSelected), updateImmediate);
}

function onToggleEntireChain(
  chainId: string,
  disabled: boolean,
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  commit(setEntireChainDisabled(chainId, disabled), updateImmediate);
}

function onAddressesChange(
  chainId: string,
  addresses: readonly string[],
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  commit(setExcludedAddresses(chainId, addresses), updateImmediate);
}
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate, loading }"
    setting="disabledChainQueries"
    :error-message="t('general_settings.disabled_chain_queries.validation.error')"
    :success-message="t('general_settings.disabled_chain_queries.validation.success')"
  >
    <div class="flex flex-col gap-3">
      <RuiAutoComplete
        :options="chains"
        :label="t('general_settings.disabled_chain_queries.chains_label')"
        :model-value="[...visibleChainIds]"
        :disabled="loading"
        data-testid="disabled-chain-queries"
        variant="outlined"
        key-attr="id"
        text-attr="name"
        chips
        hide-details
        :item-height="CHAIN_OPTION_HEIGHT_PX"
        auto-select-first
        @update:model-value="onChainsChange($event, updateImmediate)"
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
            :data-value="item.id"
            dense
            :chain="item.id"
          />
        </template>
      </RuiAutoComplete>

      <div
        v-for="chainId in visibleChainIds"
        :key="chainId"
        :data-testid="`disabled-chain-panel-${chainId}`"
        class="border border-default rounded-md p-3"
      >
        <div class="flex items-center justify-between flex-wrap gap-2">
          <ChainDisplay
            :chain="chainId"
            dense
          />
          <RuiSwitch
            :model-value="isEntireChainDisabled(chainId)"
            :disabled="loading"
            color="primary"
            hide-details
            :data-testid="`disable-entire-chain-${chainId}`"
            @update:model-value="onToggleEntireChain(chainId, $event, updateImmediate)"
          >
            {{ t('general_settings.disabled_chain_queries.disable_entire_chain') }}
          </RuiSwitch>
        </div>
        <div
          v-if="!isEntireChainDisabled(chainId)"
          class="mt-3 flex flex-col gap-1"
        >
          <ChainAccountMultiSelect
            :chain="chainId"
            :model-value="excludedAddresses[chainId] ?? []"
            :label="t('general_settings.disabled_chain_queries.exclude_addresses_label')"
            :disabled="loading"
            :data-testid="`exclude-addresses-${chainId}`"
            @update:model-value="onAddressesChange(chainId, $event, updateImmediate)"
          />
          <div
            v-if="isTransientlyDisabled(chainId)"
            :data-testid="`transient-warning-${chainId}`"
            class="text-caption text-rui-warning"
          >
            {{ t('general_settings.disabled_chain_queries.transient_warning') }}
          </div>
          <div
            v-else
            class="text-caption text-rui-text-secondary"
          >
            {{ t('general_settings.disabled_chain_queries.exclude_addresses_hint') }}
          </div>
        </div>
      </div>

      <SettingsStatusMessage
        :error="error"
        :success="success"
        data-testid="disabled-chain-queries-status"
      />
    </div>
  </SettingsOption>
</template>
