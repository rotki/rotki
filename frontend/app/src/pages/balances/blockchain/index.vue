<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import pickBy from 'lodash/pickBy';
import { type ComputedRef, type Ref } from 'vue';

type Intersections = {
  [key in Blockchain]: boolean;
};

type Observers = {
  [key in Blockchain]: (entries: IntersectionObserverEntry[]) => void;
};

type Busy = {
  [key in Blockchain]: ComputedRef<boolean>;
};

const { t, tc } = useI18n();

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
  [Blockchain.OPTIMISM]: false
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
const { ksmAccounts, dotAccounts, avaxAccounts, optimismAccounts } =
  useChainAccountBalances();
const { btcAccounts, bchAccounts } = useBtcAccountBalances();

const { blockchainAssets } = useBlockchainAggregatedBalances();

const context: ComputedRef<Blockchain> = computed(() => {
  const intersect = get(intersections);
  let currentContext = Blockchain.ETH;
  // pick only intersections that are visible (at least 50%)
  const activeObservers = pickBy(intersect, e => e);

  for (const current in activeObservers) {
    if (activeObservers[current]) {
      currentContext = current as Blockchain;
    }
  }
  return currentContext;
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
    updateWhenRatio(entries, Blockchain.OPTIMISM)
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
  [Blockchain.OPTIMISM]: isAccountOperationRunning(Blockchain.OPTIMISM)
};

const threshold = [0.5];

const { createAccount, editAccount } = useAccountDialog();

const showDetectEvmAccountsButton: Readonly<Ref<boolean>> = computedEager(
  () =>
    get(ethAccounts).length > 0 ||
    get(optimismAccounts).length > 0 ||
    get(avaxAccounts).length > 0
);
</script>

<template>
  <div>
    <v-row justify="end">
      <v-col cols="auto">
        <price-refresh />
      </v-col>
    </v-row>
    <card class="blockchain-balances mt-8" outlined-body>
      <template #title>
        {{ t('blockchain_balances.title') }}
      </template>
      <v-btn
        v-blur
        data-cy="add-blockchain-balance"
        fixed
        bottom
        right
        :fab="!$vuetify.breakpoint.xl"
        :rounded="$vuetify.breakpoint.xl"
        :x-large="$vuetify.breakpoint.xl"
        color="primary"
        @click="createAccount()"
      >
        <v-icon> mdi-plus </v-icon>
        <div v-if="$vuetify.breakpoint.xl" class="ml-2">
          {{ tc('blockchain_balances.add_account') }}
        </div>
      </v-btn>
      <account-dialog :context="context" />
      <asset-balances
        data-cy="blockchain-asset-balances"
        :loading="isBlockchainLoading"
        :title="tc('blockchain_balances.per_asset.title')"
        :balances="blockchainAssets"
      />
    </card>

    <div class="mt-8">
      <detect-evm-accounts v-if="showDetectEvmAccountsButton" />
    </div>

    <account-balances
      v-if="ethAccounts.length > 0 || busy.ETH.value"
      id="blockchain-balances-ETH"
      v-intersect="{
        handler: observers.ETH,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="tc('blockchain_balances.balances.eth')"
      :blockchain="Blockchain.ETH"
      :balances="ethAccounts"
      data-cy="blockchain-balances-ETH"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="eth2Accounts.length > 0 || busy.ETH2.value"
      id="blockchain-balances-ETH2"
      v-intersect="{
        handler: observers.ETH2,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="tc('blockchain_balances.balances.eth2')"
      :blockchain="Blockchain.ETH2"
      :balances="eth2Accounts"
      data-cy="blockchain-balances-ETH2"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="btcAccounts.length > 0 || busy.BTC.value"
      id="blockchain-balances-BTC"
      v-intersect="{
        handler: observers.BTC,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="tc('blockchain_balances.balances.btc')"
      :blockchain="Blockchain.BTC"
      :balances="btcAccounts"
      data-cy="blockchain-balances-BTC"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="bchAccounts.length > 0 || busy.BCH.value"
      id="blockchain-balances-BCH"
      v-intersect="{
        handler: observers.BCH,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="tc('blockchain_balances.balances.bch')"
      :blockchain="Blockchain.BCH"
      :balances="bchAccounts"
      data-cy="blockchain-balances-BCH"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="ksmAccounts.length > 0 || busy.KSM.value"
      id="blockchain-balances-KSM"
      v-intersect="{
        handler: observers.KSM,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="tc('blockchain_balances.balances.ksm')"
      :blockchain="Blockchain.KSM"
      :balances="ksmAccounts"
      data-cy="blockchain-balances-KSM"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="dotAccounts.length > 0 || busy.DOT.value"
      id="blockchain-balances-DOT"
      v-intersect="{
        handler: observers.DOT,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="tc('blockchain_balances.balances.dot')"
      :blockchain="Blockchain.DOT"
      :balances="dotAccounts"
      data-cy="blockchain-balances-DOT"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="avaxAccounts.length > 0 || busy.AVAX.value"
      id="blockchain-balances-AVAX"
      v-intersect="{
        handler: observers.AVAX,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="tc('blockchain_balances.balances.avax')"
      :blockchain="Blockchain.AVAX"
      :balances="avaxAccounts"
      data-cy="blockchain-balances-AVAX"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="loopringAccounts.length > 0"
      id="blockchain-balances-LRC"
      loopring
      class="mt-8"
      :title="tc('blockchain_balances.balances.loopring')"
      :blockchain="Blockchain.ETH"
      :balances="loopringAccounts"
      data-cy="blockchain-balances-LRC"
    />

    <account-balances
      v-if="optimismAccounts.length > 0 || busy.OPTIMISM.value"
      id="blockchain-balances-OPTIMISM"
      v-intersect="{
        handler: observers.OPTIMISM,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="tc('blockchain_balances.balances.optimism')"
      :blockchain="Blockchain.OPTIMISM"
      :balances="optimismAccounts"
      data-cy="blockchain-balances-OPTIMISM"
      @edit-account="editAccount($event)"
    />
  </div>
</template>
