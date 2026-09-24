<script setup lang="ts">
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { useTemplateRef } from 'vue';
import AccountBalances from '@/modules/accounts/AccountBalances.vue';
import AccountBalancesExportImport from '@/modules/accounts/AccountBalancesExportImport.vue';
import { createNewAccountForChain } from '@/modules/accounts/blockchain/new-account-state';
import AccountDialog from '@/modules/accounts/management/AccountDialog.vue';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import BlockchainBalanceStalenessIndicator from '@/modules/balances/BlockchainBalanceStalenessIndicator.vue';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { category, title } = defineProps<{
  category: string;
  title: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const account = ref<AccountManageState>();
const table = useTemplateRef<InstanceType<typeof AccountBalances>>('table');
const { isSectionLoading, refreshDisabled } = useBlockchainAccountLoading(() => category);

const { chainIds } = useAccountCategoryHelper(() => category);

function createNewBlockchainAccount(): void {
  set(account, createNewAccountForChain(get(chainIds)[0]));
}

function refresh() {
  if (isDefined(table))
    get(table).refresh();
}

const { consumeAddQuery } = useAddQuery(createNewBlockchainAccount);

onMounted(async () => {
  await consumeAddQuery();
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
        data-testid="blockchain-account-refresh"
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
        data-testid="add-blockchain-account"
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
