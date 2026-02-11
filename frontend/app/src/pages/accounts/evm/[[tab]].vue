<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';
import { useTemplateRef } from 'vue';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import AccountImportProgress from '@/components/accounts/AccountImportProgress.vue';
import EthStakingValidators from '@/components/accounts/EthStakingValidators.vue';
import EvmAccountPageButtons from '@/components/accounts/EvmAccountPageButtons.vue';
import AccountDialog from '@/components/accounts/management/AccountDialog.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import { useModules } from '@/composables/session/modules';
import { useAccountImportProgressStore } from '@/store/use-account-import-progress-store';
import { Module } from '@/types/modules';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.ACCOUNTS_EVM,
  },
  name: 'accounts-evm',
  props: true,
});

const props = defineProps<{
  tab: string;
}>();

const { tab } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('accounts-evm');

const account = ref<AccountManageState>();
const table = useTemplateRef<InstanceType<typeof AccountBalances>>('table');

const category = 'evm';
const { importingAccounts } = storeToRefs(useAccountImportProgressStore());
const { isModuleEnabled } = useModules();
const isEth2Enabled = isModuleEnabled(Module.ETH2);

const isAccountsTabSelected = computed(() => get(tab) === 'accounts');

const { chainIds } = useAccountCategoryHelper(category);
const usedChainIds = computed(() => {
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
  if (query.add) {
    const address = query.addressToAdd as string;
    createNewBlockchainAccount(address);
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
      <EvmAccountPageButtons
        :is-accounts-tab-selected="isAccountsTabSelected"
        @refresh-click="get(table)?.refreshClick()"
        @refresh="get(table)?.refresh()"
        @add-account="createNewBlockchainAccount()"
      />
    </template>

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
