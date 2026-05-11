<script setup lang="ts">
import type { ChainInfo } from '@/modules/core/api/types/chains';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

type DisabledChainQueries = Record<string, string[]>;

type ChainMode = 'all' | 'addresses';

const { t } = useI18n({ useScope: 'global' });

const { disabledChainQueries } = storeToRefs(useGeneralSettingsStore());
const { getChain, supportedChains } = useSupportedChains();
const { accounts } = storeToRefs(useBlockchainAccountsStore());

// Internal state keyed by chain.id (e.g. "polygon_pos"). Empty array => whole chain disabled.
const localValue = ref<DisabledChainQueries>({});
// Per-chain UI mode. Drives whether the address picker is shown.
const chainModes = ref<Record<string, ChainMode>>({});

// Normalize incoming dict (whose keys may be camelCased by the response transformer)
// back to chain.id form. Initial sync from the store.
watchEffect(() => {
  const raw = get(disabledChainQueries);
  const normalized: DisabledChainQueries = {};
  const modes: Record<string, ChainMode> = {};
  for (const [rawChain, addrs] of Object.entries(raw)) {
    const chain = getChain(rawChain);
    normalized[chain] = [...addrs];
    modes[chain] = addrs.length === 0 ? 'all' : 'addresses';
  }
  set(localValue, normalized);
  set(chainModes, modes);
});

const chains = computed<ChainInfo[]>(() => get(supportedChains));

const selectedChainIds = computed<string[]>(() => Object.keys(get(localValue)));

function getAddressesForChain(chainId: string): string[] {
  const list = get(accounts)[chainId] ?? [];
  const addresses = new Set<string>();
  for (const account of list) {
    const address = getAccountAddress(account);
    if (address)
      addresses.add(address);
  }
  return [...addresses].sort();
}

function isEntireChainDisabled(chainId: string): boolean {
  return get(chainModes)[chainId] === 'all';
}

// Build the dict payload to send to the backend.
// Per-address mode with zero excluded addresses => omit the chain (effectively enabled).
function buildPayload(value: DisabledChainQueries, modes: Record<string, ChainMode>): DisabledChainQueries {
  const payload: DisabledChainQueries = {};
  for (const [chain, addrs] of Object.entries(value)) {
    const mode = modes[chain] ?? 'all';
    if (mode === 'all') {
      payload[chain] = [];
    }
    else if (addrs.length > 0) {
      payload[chain] = [...addrs];
    }
  }
  return payload;
}

function commit(updateImmediate: (value: DisabledChainQueries) => void): void {
  updateImmediate(buildPayload(get(localValue), get(chainModes)));
}

function onSelectedChainsChange(
  newSelected: string[],
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  const previousValue = get(localValue);
  const previousModes = get(chainModes);
  const nextValue: DisabledChainQueries = {};
  const nextModes: Record<string, ChainMode> = {};
  for (const chain of newSelected) {
    nextValue[chain] = previousValue[chain] ?? [];
    nextModes[chain] = previousModes[chain] ?? 'all';
  }
  set(localValue, nextValue);
  set(chainModes, nextModes);
  commit(updateImmediate);
}

function setEntireChainDisabled(
  chainId: string,
  disabled: boolean,
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  set(chainModes, { ...get(chainModes), [chainId]: disabled ? 'all' : 'addresses' });
  if (disabled)
    set(localValue, { ...get(localValue), [chainId]: [] });
  commit(updateImmediate);
}

function setExcludedAddresses(
  chainId: string,
  addresses: string[],
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  set(localValue, { ...get(localValue), [chainId]: addresses });
  commit(updateImmediate);
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
        :model-value="selectedChainIds"
        :success-messages="success"
        :error-messages="error"
        :disabled="loading"
        data-cy="disabled-chain-queries"
        variant="outlined"
        key-attr="id"
        text-attr="name"
        chips
        :item-height="56"
        auto-select-first
        @update:model-value="onSelectedChainsChange($event, updateImmediate)"
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
        v-for="chainId in selectedChainIds"
        :key="chainId"
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
            @update:model-value="setEntireChainDisabled(chainId, $event, updateImmediate)"
          >
            {{ t('general_settings.disabled_chain_queries.disable_entire_chain') }}
          </RuiSwitch>
        </div>
        <div
          v-if="!isEntireChainDisabled(chainId)"
          class="mt-3"
        >
          <RuiAutoComplete
            :options="getAddressesForChain(chainId)"
            :model-value="localValue[chainId] ?? []"
            :label="t('general_settings.disabled_chain_queries.exclude_addresses_label')"
            :disabled="loading"
            variant="outlined"
            chips
            dense
            @update:model-value="setExcludedAddresses(chainId, $event, updateImmediate)"
          />
          <div class="text-caption text-rui-text-secondary mt-1">
            {{ t('general_settings.disabled_chain_queries.exclude_addresses_hint') }}
          </div>
        </div>
      </div>
    </div>
  </SettingsOption>
</template>
