<script setup lang="ts">
import { RuiProgress } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { isEqual } from 'es-toolkit';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { groupAddresses } from '@/modules/accounts/core/account-groups';
import AccountDetailsChainSection from '@/modules/accounts/details/AccountDetailsChainSection.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useChainLoadStates } from '@/modules/balances/use-balance-status';
import { useChainsWithBalances } from '@/modules/balances/use-chains-with-balances';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';

const selected = defineModel<string[] | undefined>('selected', { required: true });

const { chains, filtered = false, groupId, selectionMode = false } = defineProps<{
  groupId: string;
  /** The account's chains in scope, those switched off in the header left out. */
  chains: string[];
  /** Some of the account's chains are switched off in the header, so an empty tab may not mean an empty account. */
  filtered?: boolean;
  selectionMode?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { accounts } = storeToRefs(useBlockchainAccountsStore());
const { getChainName } = useSupportedChains();
const { isEveryAddressExcluded } = useDisabledChains();

/** The chains in scope where the account holds assets or owes liabilities; the rest get no section. */
const chainsWithBalances = useChainsWithBalances(() => groupId, () => chains);

/**
 * The chains in scope with nothing listed whose balances are still queried for this account.
 *
 * @remarks
 * Only a chain known to be empty may be left out without a word: one still loading, or one whose
 * query failed or never ran, keeps the tab from calling the account empty. A chain whose queries
 * the user switched off for every address of the account is known to have nothing to show.
 */
const queriedEmptyChains = computed<string[]>((previous) => {
  const held = get(chainsWithBalances);
  const addresses = [...groupAddresses(get(accounts), groupId)];
  const next = chains.filter(chain => !held.includes(chain) && !isEveryAddressExcluded(chain, addresses));
  return previous && isEqual(previous, next) ? previous : next;
});

const { loading: loadingChains, unloaded: unloadedChains } = useChainLoadStates(queriedEmptyChains, { untilFirstLoad: true });

const nothingToShow = computed<boolean>(() =>
  get(chainsWithBalances).length === 0 && get(loadingChains).length === 0 && get(unloadedChains).length === 0);

const unloadedNames = computed<string>(() => get(unloadedChains).map(chain => getChainName(chain)).join(', '));
</script>

<template>
  <div class="flex flex-col gap-6">
    <AccountDetailsChainSection
      v-for="chain in chainsWithBalances"
      :key="`${groupId}:${chain}`"
      v-model:selected="selected"
      :chain="chain"
      :group-id="groupId"
      :selection-mode="selectionMode"
    />
    <div
      v-if="loadingChains.length > 0"
      class="flex items-center gap-2 text-body-2 text-rui-text-secondary"
      data-testid="account-details-loading-chains"
    >
      <RuiProgress
        variant="indeterminate"
        circular
        size="16"
        thickness="2"
        color="primary"
      />
      {{ t('account_balances.loading_chain_balances', { count: loadingChains.length }, loadingChains.length) }}
    </div>
    <p
      v-if="unloadedChains.length > 0"
      class="text-body-2 text-rui-text-secondary"
      data-testid="account-details-unloaded-chains"
    >
      {{ t('account_balances.unloaded_chain_balances', { chains: unloadedNames }) }}
    </p>
    <p
      v-if="nothingToShow"
      class="text-body-2 text-rui-text-secondary"
      data-testid="account-details-no-chain-balances"
    >
      {{ filtered ? t('account_balances.no_shown_chain_balances') : t('account_balances.no_chain_balances') }}
    </p>
  </div>
</template>
