<script setup lang="ts">
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { useTemplateRef } from 'vue';
import AccountBalances from '@/modules/accounts/AccountBalances.vue';
import AccountBalancesExportImport from '@/modules/accounts/AccountBalancesExportImport.vue';
import AccountImportProgress from '@/modules/accounts/AccountImportProgress.vue';
import AccountDialog from '@/modules/accounts/management/AccountDialog.vue';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useAccountImportProgressStore } from '@/modules/accounts/use-account-import-progress-store';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import BlockchainBalanceStalenessIndicator from '@/modules/balances/BlockchainBalanceStalenessIndicator.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { category, title } = defineProps<{
  category: string;
  title: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const account = ref<AccountManageState>();
const table = useTemplateRef<InstanceType<typeof AccountBalances>>('table');
const { importingAccounts } = storeToRefs(useAccountImportProgressStore());
const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading(() => category);

const { chainIds } = useAccountCategoryHelper(() => category);

const route = useRoute();
const router = useRouter();

function createNewBlockchainAccount(): void {
  set(account, {
    chain: get(chainIds)[0],
    data: [
      {
        address: '',
        tags: null,
      },
    ],
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
      title,
    ]"
  >
    <template #buttons>
      <BlockchainBalanceStalenessIndicator class="self-center" />
      <RuiButton
        data-cy="blockchain-account-refresh"
        variant="outlined"
        color="primary"
        size="lg"
        :disabled="refreshDisabled"
        :loading="isSectionLoading"
        @click="table?.refreshClick()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
      <RuiButton
        data-cy="add-blockchain-account"
        color="primary"
        size="lg"
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
        :chain-ids="chainIds"
        @complete="refresh()"
      />
    </div>
  </TablePageLayout>
</template>
