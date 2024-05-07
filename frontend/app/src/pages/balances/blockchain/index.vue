<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type AccountManageState,
  createNewBlockchainAccount,
  editBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import type { BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

type Busy = Record<string, ComputedRef<boolean>>;

const account = ref<AccountManageState>();

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const { getBlockchainAccounts } = useBlockchainStore();

const { blockchainAssets } = useBlockchainAggregatedBalances();
const { isBlockchainLoading, isAccountOperationRunning } = useAccountLoading();
const { supportedChains, txEvmChains } = useSupportedChains();

const busy = computed<Busy>(() => Object.fromEntries(
  get(supportedChains).map(chain => ([chain.id, isAccountOperationRunning(chain.id)])),
));

const customTitles = computed<Record<string, string>>(() => ({
  [Blockchain.ETH2]: t('blockchain_balances.balances.eth2'),
}));

const accounts = computed<Record<string, BlockchainAccountWithBalance[]>>(() => Object.fromEntries(
  get(supportedChains).map(chain => [
    chain.id,
    getBlockchainAccounts(chain.id),
  ]),
));

const showDetectEvmAccountsButton: Readonly<Ref<boolean>> = computedEager(
  () => get(txEvmChains).some(chain => get(accounts)[chain.id]?.length > 0),
);

const loopringAccounts = computed<BlockchainAccountWithBalance[]>(() => getBlockchainAccounts('loopring'));

const { getChainName } = useSupportedChains();

function getTitle(chain: string) {
  const name = getChainName(chain);
  const title = get(customTitles)[chain] ?? toSentenceCase(get(name));

  return t('blockchain_balances.balances.common', { chain: title });
}

function editAccount(balanceAccount: BlockchainAccountWithBalance) {
  set(account, editBlockchainAccount(balanceAccount));
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

        <AccountDialog v-model="account" />
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

      <template v-for="chain in supportedChains">
        <AccountBalances
          v-if="accounts[chain.id] && accounts[chain.id].length > 0 || busy[chain.id].value"
          :key="chain.id"
          :title="getTitle(chain.id)"
          :blockchain="chain.id"
          :balances="accounts[chain.id]"
          @edit-account="editAccount($event)"
        />
      </template>

      <AccountBalances
        v-if="loopringAccounts.length > 0"
        loopring
        :title="t('blockchain_balances.balances.common', { chain: 'Loopring' })"
        :blockchain="Blockchain.ETH"
        :balances="loopringAccounts"
      />
    </div>
  </TablePageLayout>
</template>
