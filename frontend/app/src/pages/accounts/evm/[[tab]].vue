<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';
import { useTemplateRef } from 'vue';
import AccountBalances from '@/modules/accounts/AccountBalances.vue';
import AccountImportProgress from '@/modules/accounts/AccountImportProgress.vue';
import EthStakingValidators from '@/modules/accounts/EthStakingValidators.vue';
import EvmAccountPageButtons from '@/modules/accounts/EvmAccountPageButtons.vue';
import AccountDialog from '@/modules/accounts/management/AccountDialog.vue';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useAccountImportProgressStore } from '@/modules/accounts/use-account-import-progress-store';
import BlockchainBalanceStalenessIndicator from '@/modules/balances/BlockchainBalanceStalenessIndicator.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useEthStakingAccess } from '@/modules/staking/eth/use-eth-staking-access';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.ACCOUNTS_EVM,
  },
  name: 'accounts-evm',
  props: true,
});

const { tab } = defineProps<{
  tab: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('accounts-evm');

const account = ref<AccountManageState>();
const table = useTemplateRef<InstanceType<typeof AccountBalances>>('table');

const category = 'evm';
const { importingAccounts } = storeToRefs(useAccountImportProgressStore());
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

function createNewBlockchainAccount(address?: string): void {
  set(account, {
    chain: get(usedChainIds)[0],
    data: [
      {
        address: address || '',
        tags: null,
      },
    ],
    mode: 'add',
    type: 'account',
  });
}

function refresh(): void {
  if (isDefined(table))
    get(table).refresh();
}

function getTabLink(category: string): RouteLocationRaw {
  return {
    name: 'accounts-evm',
    params: {
      tab: category,
    },
    query: {
      keepScrollPosition: 'true',
    },
  };
}

onMounted(async () => {
  const { query } = get(route);
  if (query.add && query.addressToAdd && typeof query.addressToAdd === 'string') {
    createNewBlockchainAccount(query.addressToAdd);
    await router.replace({ query: {} });
  }
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

    <AccountImportProgress
      v-if="importingAccounts"
      class="-mb-4 -mt-1"
    />
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
