<script setup lang="ts">
import type { AccountManageState } from '@/composables/accounts/blockchain/use-account-manage';
import { useTemplateRef } from 'vue';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import AccountBalancesExportImport from '@/components/accounts/AccountBalancesExportImport.vue';
import AccountImportProgress from '@/components/accounts/AccountImportProgress.vue';
import AccountDialog from '@/components/accounts/management/AccountDialog.vue';
import BlockchainBalanceStalenessIndicator from '@/components/helper/BlockchainBalanceStalenessIndicator.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useAccountCategoryHelper } from '@/composables/accounts/use-account-category-helper';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-account-loading';
import { useAccountImportProgressStore } from '@/store/use-account-import-progress-store';

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
