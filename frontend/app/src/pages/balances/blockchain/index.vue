<script setup lang="ts">
import {
  type AccountManageState,
  createNewBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import AccountBalances from '@/components/accounts/AccountBalances.vue';

const account = ref<AccountManageState>();
const balances = ref<InstanceType<typeof AccountBalances>>();

const { t } = useI18n();

const router = useRouter();
const route = useRoute();

const { blockchainAssets } = useBlockchainAggregatedBalances();
const { isBlockchainLoading } = useAccountLoading();

function refresh() {
  if (isDefined(balances))
    get(balances).refresh();
}

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    set(account, createNewBlockchainAccount());
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.accounts_balances'), t('navigation_menu.accounts_balances_sub.blockchain_balances')]"
  >
    <template #buttons>
      <PriceRefresh />
      <RuiButton
        v-blur
        data-cy="add-blockchain-balance"
        color="primary"
        @click="account = createNewBlockchainAccount()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('blockchain_balances.add_account') }}
      </RuiButton>
    </template>

    <div class="flex flex-col gap-8">
      <RuiCard>
        <template #header>
          <CardTitle>{{ t('blockchain_balances.title') }}</CardTitle>
        </template>

        <AccountDialog
          v-model="account"
          @complete="refresh()"
        />
        <AssetBalances
          data-cy="blockchain-asset-balances"
          :loading="isBlockchainLoading"
          :title="t('blockchain_balances.per_asset.title')"
          :balances="blockchainAssets"
          sticky-header
        />
      </RuiCard>

      <AccountBalances
        ref="balances"
        @edit="account = $event"
      />
    </div>
  </TablePageLayout>
</template>
