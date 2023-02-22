<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef, type Ref } from 'vue';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import AssetBalances from '@/components/AssetBalances.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import AccountDialog from '@/components/accounts/management/AccountDialog.vue';
import { type BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

type Intersections = {
  [key in Blockchain]: boolean;
};

type Observers = {
  [key in Blockchain]: (entries: IntersectionObserverEntry[]) => void;
};

type Busy = {
  [key in Blockchain]: ComputedRef<boolean>;
};

interface BlockchainData {
  btcAccounts: Ref<BlockchainAccountWithBalance[]>;
  bchAccounts: Ref<BlockchainAccountWithBalance[]>;
  dotAccounts: Ref<BlockchainAccountWithBalance[]>;
  ethAccounts: Ref<BlockchainAccountWithBalance[]>;
  eth2Accounts: Ref<BlockchainAccountWithBalance[]>;
  avaxAccounts: Ref<BlockchainAccountWithBalance[]>;
  ksmAccounts: Ref<BlockchainAccountWithBalance[]>;
  loopringAccounts: Ref<BlockchainAccountWithBalance[]>;
  optimismAccounts: Ref<BlockchainAccountWithBalance[]>;
}

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
  [Blockchain.OPTIMISM]: false,
  [Blockchain.KSM]: false,
  [Blockchain.DOT]: false,
  [Blockchain.AVAX]: false
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

const { ethAccounts, eth2Accounts, loopringAccounts } = storeToRefs(
  useEthAccountBalancesStore()
);
const { ksmAccounts, dotAccounts, avaxAccounts, optimismAccounts } =
  storeToRefs(useChainAccountBalancesStore());
const { btcAccounts, bchAccounts } = storeToRefs(useBtcAccountBalancesStore());

const blockchainData: BlockchainData = {
  btcAccounts,
  bchAccounts,
  dotAccounts,
  ethAccounts,
  eth2Accounts,
  avaxAccounts,
  ksmAccounts,
  loopringAccounts,
  optimismAccounts
};

const { blockchainAssets } = storeToRefs(
  useAggregatedBlockchainBalancesStore()
);

const getFirstContext = (data: BlockchainData) => {
  const hasData = (data: Ref<BlockchainAccountWithBalance[]>) => {
    return get(data).length > 0;
  };

  if (hasData(data.btcAccounts)) {
    return Blockchain.BTC;
  } else if (hasData(data.bchAccounts)) {
    return Blockchain.BCH;
  } else if (hasData(data.ksmAccounts)) {
    return Blockchain.KSM;
  } else if (hasData(data.dotAccounts)) {
    return Blockchain.DOT;
  } else if (hasData(data.avaxAccounts)) {
    return Blockchain.AVAX;
  } else if (hasData(data.optimismAccounts)) {
    return Blockchain.OPTIMISM;
  }

  return Blockchain.ETH;
};

const context: ComputedRef<Blockchain> = computed(() => {
  const intersect = get(intersections);
  let currentContext = getFirstContext(blockchainData);

  for (const current in Blockchain) {
    if (intersect[current as Blockchain]) {
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

const threshold = [0];

const { createAccount, editAccount } = useAccountDialog();
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
      <detect-evm-accounts />
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
