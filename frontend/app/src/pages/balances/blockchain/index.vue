<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import type {
  AccountWithBalance,
  AccountWithBalanceAndSharedOwnership,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';
import type { ComputedRef, Ref } from 'vue';

type Busy = Record<string, ComputedRef<boolean>>;

type Account = AccountWithBalance | BlockchainAccountWithBalance | AccountWithBalanceAndSharedOwnership;

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const { ethAccounts, eth2Accounts, loopringAccounts } = useEthAccountBalances();
const { btcAccounts, bchAccounts } = useBtcAccountBalances();
const {
  ksmAccounts,
  dotAccounts,
  avaxAccounts,
  optimismAccounts,
  polygonAccounts,
  arbitrumAccounts,
  baseAccounts,
  gnosisAccounts,
  scrollAccounts,
} = useChainAccountBalances();

const { blockchainAssets } = useBlockchainAggregatedBalances();
const { isBlockchainLoading, isAccountOperationRunning } = useAccountLoading();
const { createAccount, editAccount } = useAccountDialog();
const { supportedChains } = useSupportedChains();

const busy = computed<Busy>(() => Object.fromEntries(
  get(supportedChains).map(chain => ([chain.id, isAccountOperationRunning(chain.id)])),
));

const titles = computed<Record<string, string>>(() => ({
  [Blockchain.ETH]: t('blockchain_balances.balances.eth'),
  [Blockchain.ETH2]: t('blockchain_balances.balances.eth2'),
  [Blockchain.BTC]: t('blockchain_balances.balances.btc'),
  [Blockchain.BCH]: t('blockchain_balances.balances.bch'),
  [Blockchain.KSM]: t('blockchain_balances.balances.ksm'),
  [Blockchain.DOT]: t('blockchain_balances.balances.dot'),
  [Blockchain.AVAX]: t('blockchain_balances.balances.avax'),
  [Blockchain.OPTIMISM]: t('blockchain_balances.balances.optimism'),
  [Blockchain.POLYGON_POS]: t('blockchain_balances.balances.polygon_pos'),
  [Blockchain.ARBITRUM_ONE]: t('blockchain_balances.balances.arbitrum_one'),
  [Blockchain.BASE]: t('blockchain_balances.balances.base'),
  [Blockchain.GNOSIS]: t('blockchain_balances.balances.gnosis'),
  [Blockchain.SCROLL]: t('blockchain_balances.balances.scroll'),
}));

const accounts = computed<Record<string, Account[]>>(() => ({
  [Blockchain.ETH]: get(ethAccounts),
  [Blockchain.ETH2]: get(eth2Accounts),
  [Blockchain.BTC]: get(btcAccounts),
  [Blockchain.BCH]: get(bchAccounts),
  [Blockchain.KSM]: get(ksmAccounts),
  [Blockchain.DOT]: get(dotAccounts),
  [Blockchain.AVAX]: get(avaxAccounts),
  [Blockchain.OPTIMISM]: get(optimismAccounts),
  [Blockchain.POLYGON_POS]: get(polygonAccounts),
  [Blockchain.ARBITRUM_ONE]: get(arbitrumAccounts),
  [Blockchain.BASE]: get(baseAccounts),
  [Blockchain.GNOSIS]: get(gnosisAccounts),
  [Blockchain.SCROLL]: get(scrollAccounts),
}));

const showDetectEvmAccountsButton: Readonly<Ref<boolean>> = computedEager(
  () =>
    get(ethAccounts).length > 0
    || get(optimismAccounts).length > 0
    || get(avaxAccounts).length > 0
    || get(polygonAccounts).length > 0
    || get(arbitrumAccounts).length > 0
    || get(baseAccounts).length > 0
    || get(gnosisAccounts).length > 0
    || get(scrollAccounts).length > 0,
);

function getTitle(chain: string) {
  return get(titles)[chain] ?? '';
}

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
        :title="t('blockchain_balances.balances.loopring')"
        :blockchain="Blockchain.ETH"
        :balances="loopringAccounts"
      />
    </div>
  </TablePageLayout>
</template>
