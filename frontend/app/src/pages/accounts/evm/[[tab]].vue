<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';
import { useTemplateRef } from 'vue';
import { msg } from '@/message-key';
import AccountBalances from '@/modules/accounts/AccountBalances.vue';
import { type AddAccountSeed, parseAddAccountLink } from '@/modules/accounts/add-account-link';
import { createNewAccountForChain } from '@/modules/accounts/blockchain/new-account-state';
import EthStakingValidators from '@/modules/accounts/EthStakingValidators.vue';
import EvmAccountPageButtons from '@/modules/accounts/EvmAccountPageButtons.vue';
import AccountDialog from '@/modules/accounts/management/AccountDialog.vue';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import BlockchainBalanceStalenessIndicator from '@/modules/balances/BlockchainBalanceStalenessIndicator.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useEthStakingAccess } from '@/modules/staking/eth/use-eth-staking-access';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.accounts_sub.evm'), icon: 'lu-evm-accounts', parent: '/accounts/', order: 10, drawer: 'accounts-evm', addAction: { labelKey: msg.$t('blockchain_balances.form_dialog.add_title') } },
    canNavigateBack: true,
    noteLocation: NoteLocation.ACCOUNTS_EVM,
  },
  props: true,
});

const { tab } = defineProps<{
  tab: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('/accounts/evm/[[tab]]');

const account = ref<AccountManageState>();
const table = useTemplateRef<InstanceType<typeof AccountBalances>>('table');

const category = 'evm';
const { enabled: isEth2Enabled } = useModuleEnabled(Module.ETH2);
const { chainIds } = useAccountCategoryHelper(category);
const { allowed: ethStakingAllowed } = useEthStakingAccess();

const isAccountsTabSelected = computed<boolean>(() => tab === 'accounts');
const isAddDisabled = computed<boolean>(() => !get(isAccountsTabSelected) && !get(ethStakingAllowed));

const usedChainIds = computed<string[]>(() => {
  if (get(isAccountsTabSelected)) {
    return [
      'all',
      ...get(chainIds),
    ];
  }

  return [Blockchain.ETH2];
});

/**
 * Opens the add dialog, optionally holding addresses on a chain. A chain the tab does not offer is
 * ignored rather than trusted, so a link cannot open the dialog on something it cannot add to.
 */
function createNewBlockchainAccount({ addresses, chain }: AddAccountSeed = { addresses: [] }): void {
  const usable = get(usedChainIds);
  const state = createNewAccountForChain(chain && usable.includes(chain) ? chain : usable[0]);

  if (addresses.length > 0 && state.type === 'account')
    state.data = addresses.map(address => ({ address, tags: null }));

  set(account, state);
}

function refresh(): void {
  if (isDefined(table))
    get(table).refresh();
}

function getTabLink(category: string): RouteLocationRaw {
  return {
    name: '/accounts/evm/[[tab]]',
    params: {
      tab: category,
    },
    query: {
      keepScrollPosition: 'true',
    },
  };
}

const { consumeAddQuery } = useAddQuery((query) => {
  createNewBlockchainAccount(parseAddAccountLink(query));
});

onMounted(async () => {
  await consumeAddQuery();
});

watchImmediate(route, (route) => {
  const { params } = route;

  if (!params.tab) {
    router.replace(getTabLink('accounts'));
  }
}, { deep: true });
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.accounts'),
      t('navigation_menu.accounts_sub.evm'),
    ]"
  >
    <template #buttons>
      <BlockchainBalanceStalenessIndicator class="self-center" />
      <EvmAccountPageButtons
        :is-accounts-tab-selected="isAccountsTabSelected"
        :add-disabled="isAddDisabled"
        @refresh-click="get(table)?.refreshClick()"
        @refresh="get(table)?.refresh()"
        @add-account="createNewBlockchainAccount()"
      />
    </template>

    <template #tabs>
      <RuiTabs
        color="primary"
        class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
      >
        <RuiTab
          link
          :to="getTabLink('accounts')"
        >
          {{ t('blockchain_balances.tabs.accounts') }}
        </RuiTab>
        <RuiTab
          v-if="isEth2Enabled"
          link
          :to="getTabLink('validators')"
        >
          {{ t('blockchain_balances.tabs.validators') }}
        </RuiTab>
      </RuiTabs>
    </template>

    <Transition
      enter-from-class="opacity-0 translate-x-8"
      enter-active-class="w-full transform duration-300 transition"
      enter-to-class="opacity-100 translate-x-0"
      leave-active-class="hidden"
    >
      <AccountBalances
        v-if="isAccountsTabSelected"
        ref="table"
        :category="category"
        @edit="account = $event"
      />
      <EthStakingValidators
        v-else
        ref="table"
        @edit="account = $event"
      />
    </Transition>
    <AccountDialog
      v-model="account"
      :chain-ids="usedChainIds"
      :show-all-chains-option="isAccountsTabSelected"
      @complete="refresh()"
    />
  </TablePageLayout>
</template>
