<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { pickBy } from 'lodash-es';
import { type ComputedRef, type Ref } from 'vue';

const { t } = useI18n();

type Intersections = {
  [key in Blockchain]: boolean;
};

type Observers = {
  [key in Blockchain]: (entries: IntersectionObserverEntry[]) => void;
};

type Busy = {
  [key in Blockchain]: ComputedRef<boolean>;
};

const router = useRouter();
const route = useRoute();

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    createAccount();
    await router.replace({ query: {} });
  }
});

const intersections = ref<Intersections>({
  [Blockchain.ETH]: false,
  [Blockchain.ETH2]: false,
  [Blockchain.BTC]: false,
  [Blockchain.BCH]: false,
  [Blockchain.KSM]: false,
  [Blockchain.DOT]: false,
  [Blockchain.AVAX]: false,
  [Blockchain.OPTIMISM]: false,
  [Blockchain.POLYGON_POS]: false,
  [Blockchain.ARBITRUM_ONE]: false,
  [Blockchain.BASE]: false
});

const updateWhenRatio = (
  entries: IntersectionObserverEntry[],
  value: Blockchain
) => {
  set(intersections, {
    ...get(intersections),
    [value]: entries[0].isIntersecting
  });
};

const { ethAccounts, eth2Accounts, loopringAccounts } = useEthAccountBalances();
const {
  ksmAccounts,
  dotAccounts,
  avaxAccounts,
  optimismAccounts,
  polygonAccounts,
  arbitrumAccounts,
  baseAccounts
} = useChainAccountBalances();
const { btcAccounts, bchAccounts } = useBtcAccountBalances();

const { blockchainAssets } = useBlockchainAggregatedBalances();

const context: ComputedRef<Blockchain> = computed(() => {
  // pick only intersections that are visible (at least 50%)
  const activeObservers = Object.keys(pickBy(get(intersections), e => e));

  if (activeObservers.length > 0) {
    return activeObservers[activeObservers.length - 1] as Blockchain;
  }

  return Blockchain.ETH;
});

const observers: Observers = {
  [Blockchain.ETH]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.ETH),
  [Blockchain.ETH2]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.ETH2),
  [Blockchain.BTC]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.BTC),
  [Blockchain.BCH]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.BCH),
  [Blockchain.KSM]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.KSM),
  [Blockchain.DOT]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.DOT),
  [Blockchain.AVAX]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.AVAX),
  [Blockchain.OPTIMISM]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.OPTIMISM),
  [Blockchain.POLYGON_POS]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.POLYGON_POS),
  [Blockchain.ARBITRUM_ONE]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.ARBITRUM_ONE),
  [Blockchain.BASE]: (entries: IntersectionObserverEntry[]) =>
    updateWhenRatio(entries, Blockchain.BASE)
};

const { isBlockchainLoading, isAccountOperationRunning } = useAccountLoading();

const busy: Busy = {
  [Blockchain.ETH]: isAccountOperationRunning(Blockchain.ETH),
  [Blockchain.ETH2]: isAccountOperationRunning(Blockchain.ETH2),
  [Blockchain.BTC]: isAccountOperationRunning(Blockchain.BTC),
  [Blockchain.BCH]: isAccountOperationRunning(Blockchain.BCH),
  [Blockchain.KSM]: isAccountOperationRunning(Blockchain.KSM),
  [Blockchain.DOT]: isAccountOperationRunning(Blockchain.DOT),
  [Blockchain.AVAX]: isAccountOperationRunning(Blockchain.AVAX),
  [Blockchain.OPTIMISM]: isAccountOperationRunning(Blockchain.OPTIMISM),
  [Blockchain.POLYGON_POS]: isAccountOperationRunning(Blockchain.POLYGON_POS),
  [Blockchain.ARBITRUM_ONE]: isAccountOperationRunning(Blockchain.ARBITRUM_ONE),
  [Blockchain.BASE]: isAccountOperationRunning(Blockchain.BASE)
};

const threshold = [0.5];

const { createAccount, editAccount } = useAccountDialog();

const showDetectEvmAccountsButton: Readonly<Ref<boolean>> = computedEager(
  () =>
    get(ethAccounts).length > 0 ||
    get(optimismAccounts).length > 0 ||
    get(avaxAccounts).length > 0 ||
    get(polygonAccounts).length > 0 ||
    get(arbitrumAccounts).length > 0 ||
    get(baseAccounts).length > 0
);
</script>

<template>
  <TablePageLayout>
    <template #title>
      <span class="text-rui-text-secondary">
        {{ t('navigation_menu.accounts_balances') }} /
      </span>
      {{ t('navigation_menu.accounts_balances_sub.blockchain_balances') }}
    </template>
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

    <RuiCard>
      <template #header>
        <CardTitle>{{ t('blockchain_balances.title') }}</CardTitle>
      </template>

      <AccountDialog :context="context" />
      <AssetBalances
        data-cy="blockchain-asset-balances"
        :loading="isBlockchainLoading"
        :title="t('blockchain_balances.per_asset.title')"
        :balances="blockchainAssets"
      />
    </RuiCard>

    <div class="mt-8">
      <DetectEvmAccounts v-if="showDetectEvmAccountsButton" />
    </div>

    <AccountBalances
      v-if="ethAccounts.length > 0 || busy.eth.value"
      :id="`blockchain-balances-${Blockchain.ETH}`"
      v-intersect="{
        handler: observers.eth,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.eth')"
      :blockchain="Blockchain.ETH"
      :balances="ethAccounts"
      :data-cy="`blockchain-balances-${Blockchain.ETH}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="eth2Accounts.length > 0 || busy.eth2.value"
      :id="`blockchain-balances-${Blockchain.ETH2}`"
      v-intersect="{
        handler: observers.eth2,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.eth2')"
      :blockchain="Blockchain.ETH2"
      :balances="eth2Accounts"
      :data-cy="`blockchain-balances-${Blockchain.ETH2}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="btcAccounts.length > 0 || busy.btc.value"
      :id="`blockchain-balances-${Blockchain.BTC}`"
      v-intersect="{
        handler: observers.btc,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.btc')"
      :blockchain="Blockchain.BTC"
      :balances="btcAccounts"
      :data-cy="`blockchain-balances-${Blockchain.BTC}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="bchAccounts.length > 0 || busy.bch.value"
      :id="`blockchain-balances-${Blockchain.BCH}`"
      v-intersect="{
        handler: observers.bch,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.bch')"
      :blockchain="Blockchain.BCH"
      :balances="bchAccounts"
      :data-cy="`blockchain-balances-${Blockchain.BCH}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="ksmAccounts.length > 0 || busy.ksm.value"
      :id="`blockchain-balances-${Blockchain.KSM}`"
      v-intersect="{
        handler: observers.ksm,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.ksm')"
      :blockchain="Blockchain.KSM"
      :balances="ksmAccounts"
      :data-cy="`blockchain-balances-${Blockchain.KSM}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="dotAccounts.length > 0 || busy.dot.value"
      :id="`blockchain-balances-${Blockchain.DOT}`"
      v-intersect="{
        handler: observers.dot,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.dot')"
      :blockchain="Blockchain.DOT"
      :balances="dotAccounts"
      data-cy="blockchain-balances-DOT"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="avaxAccounts.length > 0 || busy.avax.value"
      :id="`blockchain-balances-${Blockchain.AVAX}`"
      v-intersect="{
        handler: observers.avax,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.avax')"
      :blockchain="Blockchain.AVAX"
      :balances="avaxAccounts"
      :data-cy="`blockchain-balances-${Blockchain.AVAX}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="optimismAccounts.length > 0 || busy.optimism.value"
      :id="`blockchain-balances-${Blockchain.OPTIMISM}`"
      v-intersect="{
        handler: observers.optimism,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.optimism')"
      :blockchain="Blockchain.OPTIMISM"
      :balances="optimismAccounts"
      :data-cy="`blockchain-balances-${Blockchain.OPTIMISM}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="polygonAccounts.length > 0 || busy.polygon_pos.value"
      :id="`blockchain-balances-${Blockchain.POLYGON_POS}`"
      v-intersect="{
        handler: observers.polygon_pos,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.polygon_pos')"
      :blockchain="Blockchain.POLYGON_POS"
      :balances="polygonAccounts"
      :data-cy="`blockchain-balances-${Blockchain.POLYGON_POS}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="arbitrumAccounts.length > 0 || busy.arbitrum_one.value"
      :id="`blockchain-balances-${Blockchain.ARBITRUM_ONE}`"
      v-intersect="{
        handler: observers.arbitrum_one,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.arbitrum_one')"
      :blockchain="Blockchain.ARBITRUM_ONE"
      :balances="arbitrumAccounts"
      :data-cy="`blockchain-balances-${Blockchain.ARBITRUM_ONE}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="baseAccounts.length > 0 || busy.base.value"
      :id="`blockchain-balances-${Blockchain.BASE}`"
      v-intersect="{
        handler: observers.base,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="t('blockchain_balances.balances.base')"
      :blockchain="Blockchain.BASE"
      :balances="baseAccounts"
      :data-cy="`blockchain-balances-${Blockchain.BASE}`"
      @edit-account="editAccount($event)"
    />

    <AccountBalances
      v-if="loopringAccounts.length > 0"
      id="blockchain-balances-LRC"
      loopring
      class="mt-8"
      :title="t('blockchain_balances.balances.loopring')"
      :blockchain="Blockchain.ETH"
      :balances="loopringAccounts"
      data-cy="blockchain-balances-LRC"
    />
  </TablePageLayout>
</template>
