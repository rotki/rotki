<script setup lang="ts">
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { useTemplateRef } from 'vue';
import AccountBalances from '@/modules/accounts/AccountBalances.vue';
import AccountBalancesExportImport from '@/modules/accounts/AccountBalancesExportImport.vue';
import AccountsRefreshButton from '@/modules/accounts/AccountsRefreshButton.vue';
import AccountsStalenessIndicator from '@/modules/accounts/AccountsStalenessIndicator.vue';
import { createNewAccountForChain } from '@/modules/accounts/blockchain/new-account-state';
import AccountDialog from '@/modules/accounts/management/AccountDialog.vue';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { addLabel, category, title } = defineProps<{
  category: string;
  title: string;
  addLabel: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const account = ref<AccountManageState>();
const table = useTemplateRef<InstanceType<typeof AccountBalances>>('table');

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
      <AccountsStalenessIndicator
        class="self-center"
        :category="category"
      />
      <AccountsRefreshButton
        :category="category"
        @refresh="table?.refreshClick($event)"
      />
      <RuiButton
        data-testid="add-blockchain-account"
        color="primary"
        @click="createNewBlockchainAccount()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ addLabel }}
      </RuiButton>

      <AccountBalancesExportImport />
    </template>
    <div>
      <AccountBalances
        ref="table"
        :category="category"
        @edit="account = $event"
        @add="createNewBlockchainAccount()"
      />

      <AccountDialog
        v-model="account"
        :chain-ids="chainIds"
        @complete="refresh()"
      />
    </div>
  </TablePageLayout>
</template>
