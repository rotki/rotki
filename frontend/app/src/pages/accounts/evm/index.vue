<script setup lang="ts">
import { useTemplateRef } from 'vue';
import { NoteLocation } from '@/types/notes';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useAccountImportProgressStore } from '@/store/use-account-import-progress-store';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import AccountBalancesExportImport from '@/components/accounts/AccountBalancesExportImport.vue';
import BlockchainBalanceRefreshBehaviourMenu
  from '@/components/dashboard/blockchain-balance/BlockchainBalanceRefreshBehaviourMenu.vue';
import AccountDialog from '@/components/accounts/management/AccountDialog.vue';
import AccountImportProgress from '@/components/accounts/AccountImportProgress.vue';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.ACCOUNTS_EVM,
  },
  name: 'accounts-evm',
});

const { t } = useI18n();

const account = ref<AccountManageState>();
const table = useTemplateRef<InstanceType<typeof AccountBalances>>('table');

const category = 'evm';
const { importingAccounts } = storeToRefs(useAccountImportProgressStore());
const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading(category);

const router = useRouter();
const route = useRoute();

const { chainIds } = useAccountCategoryHelper(category);

function createNewBlockchainAccount(): void {
  set(account, {
    chain: get(chainIds)[0],
    data: [
      {
        address: '',
        tags: null,
      },
    ],
    evm: true,
    mode: 'add',
    type: 'account',
  });
}

function refresh() {
  if (isDefined(table))
    get(table).refresh();
}

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    createNewBlockchainAccount();
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.accounts'),
      t('navigation_menu.accounts_sub.evm'),
    ]"
  >
    <template #buttons>
      <RuiButtonGroup
        variant="outlined"
        color="primary"
      >
        <RuiButton
          :disabled="refreshDisabled"
          :loading="isSectionLoading"
          @click="table?.refreshClick()"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
        <RuiMenu>
          <template #activator="{ attrs }">
            <RuiButton
              v-bind="attrs"
              color="primary"
              variant="outlined"
              class="!outline-0 px-2"
            >
              <RuiIcon name="lu-chevron-down" />
            </RuiButton>
          </template>

          <BlockchainBalanceRefreshBehaviourMenu />
        </RuiMenu>
      </RuiButtonGroup>

      <RuiButton
        data-cy="add-blockchain-account"
        color="primary"
        @click="createNewBlockchainAccount()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('blockchain_balances.add_account') }}
      </RuiButton>

      <AccountBalancesExportImport />
    </template>
    <div>
      <AccountImportProgress
        v-if="importingAccounts"
        class="-mb-4 -mt-1"
      />

      <AccountBalances
        ref="table"
        :category="category"
        @edit="account = $event"
      />

      <AccountDialog
        v-model="account"
        @complete="refresh()"
      />
    </div>
  </TablePageLayout>
</template>
