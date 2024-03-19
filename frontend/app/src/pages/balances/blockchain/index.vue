<script setup lang="ts">
const { t } = useI18n();

const router = useRouter();
const route = useRoute();

const { blockchainAssets } = useBlockchainAggregatedBalances();

const { isBlockchainLoading } = useAccountLoading();

const { createAccount } = useAccountDialog();

const showDetectEvmAccountsButton: Readonly<Ref<boolean>> = computedEager(
  () => true, // todo check for any evm chain accounts
);

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    createAccount();
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.accounts_balances'),
      t('navigation_menu.accounts_balances_sub.blockchain_balances'),
    ]"
  >
    <template #buttons>
      <PriceRefresh />
      <RuiButton
        v-blur
        data-cy="add-blockchain-balance"
        color="primary"
        @click="createAccount()"
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

        <AccountDialog />
        <AssetBalances
          data-cy="blockchain-asset-balances"
          :loading="isBlockchainLoading"
          :title="t('blockchain_balances.per_asset.title')"
          :balances="blockchainAssets"
          sticky-header
        />
      </RuiCard>

      <div>
        <DetectEvmAccounts v-if="showDetectEvmAccountsButton" />
      </div>

      <AccountBalances />
    </div>
  </TablePageLayout>
</template>
