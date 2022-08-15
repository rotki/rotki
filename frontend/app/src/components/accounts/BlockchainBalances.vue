<template>
  <div>
    <price-refresh />
    <card class="blockchain-balances mt-8" outlined-body>
      <template #title>
        {{ $t('blockchain_balances.title') }}
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
          {{ $tc('blockchain_balances.add_account') }}
        </div>
      </v-btn>
      <big-dialog
        :display="openDialog"
        :title="dialogTitle"
        :subtitle="dialogSubtitle"
        :primary-action="$tc('common.actions.save')"
        :secondary-action="$tc('common.actions.cancel')"
        :action-disabled="!valid"
        @confirm="saveAccount()"
        @cancel="clearDialog()"
      >
        <account-form
          ref="form"
          v-model="valid"
          :edit="accountToEdit"
          :context="context"
        />
      </big-dialog>
      <asset-balances
        data-cy="blockchain-asset-balances"
        :loading="balancesLoading"
        :title="$t('blockchain_balances.per_asset.title')"
        :balances="blockchainAssets"
      />
    </card>

    <account-balances
      v-if="ethAccounts.length > 0"
      id="blockchain-balances-ETH"
      v-intersect="{
        handler: observers.ETH,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="$t('blockchain_balances.balances.eth')"
      blockchain="ETH"
      :balances="ethAccounts"
      data-cy="blockchain-balances-ETH"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="eth2Accounts.length > 0"
      id="blockchain-balances-ETH2"
      v-intersect="{
        handler: observers.ETH2,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="$t('blockchain_balances.balances.eth2')"
      blockchain="ETH2"
      :balances="eth2Accounts"
      data-cy="blockchain-balances-ETH2"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="btcAccounts.length > 0"
      id="blockchain-balances-BTC"
      v-intersect="{
        handler: observers.BTC,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="$t('blockchain_balances.balances.btc')"
      blockchain="BTC"
      :balances="btcAccounts"
      data-cy="blockchain-balances-BTC"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="bchAccounts.length > 0"
      id="blockchain-balances-BCH"
      v-intersect="{
        handler: observers.BCH,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="$t('blockchain_balances.balances.bch')"
      blockchain="BCH"
      :balances="bchAccounts"
      data-cy="blockchain-balances-BCH"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="ksmAccounts.length > 0"
      id="blockchain-balances-KSM"
      v-intersect="{
        handler: observers.KSM,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="$t('blockchain_balances.balances.ksm')"
      blockchain="KSM"
      :balances="ksmAccounts"
      data-cy="blockchain-balances-KSM"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="dotAccounts.length > 0"
      id="blockchain-balances-DOT"
      v-intersect="{
        handler: observers.DOT,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="$t('blockchain_balances.balances.dot')"
      blockchain="DOT"
      :balances="dotAccounts"
      data-cy="blockchain-balances-DOT"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="avaxAccounts.length > 0"
      id="blockchain-balances-AVAX"
      v-intersect="{
        handler: observers.AVAX,
        options: {
          threshold
        }
      }"
      class="mt-8"
      :title="$t('blockchain_balances.balances.avax')"
      blockchain="AVAX"
      :balances="avaxAccounts"
      data-cy="blockchain-balances-AVAX"
      @edit-account="editAccount($event)"
    />

    <account-balances
      v-if="loopringAccounts.length > 0"
      id="blockchain-balances-LRC"
      loopring
      class="mt-8"
      :title="$t('blockchain_balances.balances.loopring')"
      blockchain="ETH"
      :balances="loopringAccounts"
      data-cy="blockchain-balances-LRC"
    />
  </div>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  onMounted,
  Ref,
  ref
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import AccountForm, {
  AccountFormType
} from '@/components/accounts/AccountForm.vue';
import AssetBalances from '@/components/AssetBalances.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import { useRoute, useRouter } from '@/composables/common';
import i18n from '@/i18n';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { BlockchainAccountWithBalance } from '@/store/balances/types';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

type Intersections = {
  [key in Blockchain]: boolean;
};

type BlockchainData = {
  btcAccounts: Ref<BlockchainAccountWithBalance[]>;
  bchAccounts: Ref<BlockchainAccountWithBalance[]>;
  dotAccounts: Ref<BlockchainAccountWithBalance[]>;
  ethAccounts: Ref<BlockchainAccountWithBalance[]>;
  eth2Accounts: Ref<BlockchainAccountWithBalance[]>;
  avaxAccounts: Ref<BlockchainAccountWithBalance[]>;
  ksmAccounts: Ref<BlockchainAccountWithBalance[]>;
  loopringAccounts: Ref<BlockchainAccountWithBalance[]>;
};

const BlockchainBalances = defineComponent({
  name: 'BlockchainBalances',
  components: {
    PriceRefresh,
    AccountForm,
    AccountBalances,
    AssetBalances,
    BigDialog
  },
  setup() {
    const accountToEdit = ref<BlockchainAccountWithBalance | null>(null);
    const dialogTitle = ref('');
    const dialogSubtitle = ref('');
    const valid = ref(false);
    const openDialog = ref(false);
    const form = ref<AccountFormType | null>(null);

    const createAccount = () => {
      set(accountToEdit, null);
      set(
        dialogTitle,
        i18n.t('blockchain_balances.form_dialog.add_title').toString()
      );
      set(dialogSubtitle, '');
      set(openDialog, true);
    };

    const editAccount = (account: BlockchainAccountWithBalance) => {
      set(accountToEdit, account);
      set(
        dialogTitle,
        i18n.t('blockchain_balances.form_dialog.edit_title').toString()
      );
      set(
        dialogSubtitle,
        i18n.t('blockchain_balances.form_dialog.edit_subtitle').toString()
      );
      set(openDialog, true);
    };

    const clearDialog = async () => {
      set(openDialog, false);
      setTimeout(async () => {
        if (get(form)) {
          await get(form)!.reset();
        }
        set(accountToEdit, null);
      }, 300);
    };

    const saveAccount = async () => {
      if (!get(form)) {
        return;
      }
      const success = await get(form)!.save();
      if (success) {
        await clearDialog();
      }
    };

    const router = useRouter();
    const route = useRoute();

    onMounted(() => {
      const query = get(route).query;

      if (query.add) {
        createAccount();
        router.replace({ query: {} });
      }
    });

    const intersections = ref<Intersections>({
      [Blockchain.ETH]: false,
      [Blockchain.ETH2]: false,
      [Blockchain.BTC]: false,
      [Blockchain.BCH]: false,
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

    const {
      btcAccounts,
      bchAccounts,
      dotAccounts,
      ethAccounts,
      eth2Accounts,
      avaxAccounts,
      ksmAccounts,
      loopringAccounts
    } = storeToRefs(useBlockchainAccountsStore());

    const blockchainData: BlockchainData = {
      btcAccounts,
      bchAccounts,
      dotAccounts,
      ethAccounts,
      eth2Accounts,
      avaxAccounts,
      ksmAccounts,
      loopringAccounts
    };

    const { blockchainAssets } = storeToRefs(useBlockchainBalancesStore());

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
      }

      return Blockchain.ETH;
    };

    const context = computed(() => {
      const intersect = get(intersections);
      let currentContext = getFirstContext(blockchainData);

      for (const current in Blockchain) {
        if (intersect[current as Blockchain]) {
          currentContext = current as Blockchain;
        }
      }
      return currentContext;
    });

    const observers = {
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
        updateWhenRatio(entries, Blockchain.AVAX)
    };

    const { isTaskRunning } = useTasks();

    const isQueryingBlockchain = isTaskRunning(
      TaskType.QUERY_BLOCKCHAIN_BALANCES
    );
    const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);

    const isBlockchainLoading = computed<boolean>(() => {
      return get(isQueryingBlockchain) || get(isLoopringLoading);
    });

    return {
      balancesLoading: isBlockchainLoading,
      form,
      context,
      accountToEdit,
      dialogTitle,
      dialogSubtitle,
      valid,
      openDialog,
      createAccount,
      editAccount,
      clearDialog,
      saveAccount,
      observers,
      ...blockchainData,
      blockchainAssets,
      threshold: [1]
    };
  }
});

export default BlockchainBalances;
</script>
