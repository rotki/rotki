<template>
  <v-card :class="`${blockchain.toLocaleLowerCase()}-account-balances`">
    <v-card-title>
      <v-row align="center" no-gutters>
        <v-col cols="auto">
          <refresh-button
            class="account-balances__refresh"
            :loading="isLoading"
            :tooltip="tc('account_balances.refresh_tooltip', 0, { blockchain })"
            @refresh="refreshBlockchainBalances"
          />
        </v-col>
        <v-col class="ps-2">
          <card-title>{{ title }}</card-title>
        </v-col>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-row class="mb-2">
        <v-col cols="12" sm="6">
          <v-tooltip top>
            <template #activator="{ on, attrs }">
              <span v-bind="attrs" v-on="on">
                <v-btn
                  data-cy="account-balances__delete-button"
                  color="red"
                  text
                  outlined
                  :disabled="
                    isLoading ||
                    operationRunning ||
                    selectedAddresses.length === 0
                  "
                  @click="confirmDelete = true"
                >
                  <v-icon> mdi-delete-outline </v-icon>
                  <span>{{ tc('common.actions.delete') }}</span>
                </v-btn>
              </span>
            </template>
            <span>{{ tc('account_balances.delete_tooltip') }}</span>
          </v-tooltip>
          <v-tooltip v-if="isEth" top>
            <template #activator="{ on }">
              <v-btn
                class="ml-2"
                text
                outlined
                :loading="detectingTokens"
                :disabled="detectingTokens || isLoading"
                v-on="on"
                @click="redetectAllTokens"
              >
                <v-icon class="mr-2">mdi-refresh</v-icon>
                {{ tc('account_balances.detect_tokens.tooltip.redetect') }}
              </v-btn>
            </template>
            <span>
              {{ tc('account_balances.detect_tokens.tooltip.redetect_all') }}
            </span>
          </v-tooltip>
        </v-col>
        <v-col v-if="!isEth2" cols="12" sm="6">
          <tag-filter v-model="visibleTags" hide-details />
        </v-col>
      </v-row>
      <account-balance-table
        ref="balanceTable"
        data-cy="blockchain-balances"
        :loopring="loopring"
        :blockchain="blockchain"
        :balances="balances"
        :visible-tags="visibleTags"
        :selected="selectedAddresses"
        @edit-click="editAccount($event)"
        @delete-xpub="xpubToDelete = $event"
        @addresses-selected="selectedAddresses = $event"
      />
      <confirm-dialog
        :display="deleteConfirmed"
        :title="tc('account_balances.confirm_delete.title')"
        :message="deleteDescription"
        @cancel="cancelDelete()"
        @confirm="deleteAccount()"
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import AccountBalanceTable from '@/components/accounts/AccountBalanceTable.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useRefresh } from '@/composables/balances/refresh';
import { useTokenDetection } from '@/composables/balances/token-detection';
import {
  AccountWithBalance,
  BlockchainAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { useBlockchainStore } from '@/store/blockchain';
import { useBlockchainAccountsStore } from '@/store/blockchain/accounts';
import { useBtcAccountsStore } from '@/store/blockchain/accounts/btc';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { startPromise } from '@/utils';

const props = defineProps({
  balances: { required: true, type: Array as PropType<AccountWithBalance[]> },
  blockchain: { required: true, type: String as PropType<Blockchain> },
  title: { required: true, type: String },
  loopring: { required: false, type: Boolean, default: false }
});

const emit = defineEmits<{
  (e: 'edit-account', account: BlockchainAccountWithBalance): void;
}>();

const { blockchain } = toRefs(props);

const { isTaskRunning } = useTasks();
const { refreshBlockchainBalances } = useRefresh(blockchain);
const { detectingTokens } = useTokenDetection();

const redetectAllTokens = () => {
  get(balanceTable)?.fetchAllDetectedTokensAndQueryBalance();
};

const selectedAddresses = ref<string[]>([]);
const visibleTags = ref<string[]>([]);
const editedAccount = ref<string>('');
const confirmDelete = ref<boolean>(false);
const xpubToDelete = ref<XpubPayload | null>(null);
const balanceTable = ref<any>(null);

const { tc } = useI18n();

const isEth2 = computed<boolean>(() => {
  return get(blockchain) === Blockchain.ETH2;
});

const isEth = computed<boolean>(() => {
  return get(blockchain) === Blockchain.ETH;
});

const isQueryingBlockchain = isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);

const isLoading = computed<boolean>(() => {
  if (!get(isEth2)) {
    return get(isQueryingBlockchain);
  }
  const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);

  return get(isQueryingBlockchain) || get(isLoopringLoading);
});

const operationRunning = computed<boolean>(() => {
  return (
    get(isTaskRunning(TaskType.ADD_ACCOUNT)) ||
    get(isTaskRunning(TaskType.REMOVE_ACCOUNT))
  );
});

const deleteConfirmed = computed<boolean>(() => {
  return get(confirmDelete) || !!get(xpubToDelete);
});

const deleteDescription = computed<string>(() => {
  if (get(xpubToDelete)) {
    return tc('account_balances.confirm_delete.description_xpub', 0, {
      address: get(xpubToDelete)!.xpub
    });
  }
  return tc('account_balances.confirm_delete.description_address', 0, {
    count: get(selectedAddresses).length
  });
});

const editAccount = (account: BlockchainAccountWithBalance) => {
  set(editedAccount, account.address);
  emit('edit-account', account);
};

const { deleteEth2Validators } = useEthAccountsStore();
const { removeAccount } = useBlockchainAccountsStore();
const { refreshAccounts } = useBlockchainStore();
const { deleteXpub } = useBtcAccountsStore();

const deleteAccount = async () => {
  if (get(selectedAddresses).length > 0) {
    set(confirmDelete, false);

    if (get(isEth2)) {
      await deleteEth2Validators(get(selectedAddresses));
    } else {
      await removeAccount({
        accounts: get(selectedAddresses),
        blockchain: get(blockchain)
      });
    }

    startPromise(refreshAccounts(blockchain));
    set(selectedAddresses, []);
  } else if (get(xpubToDelete)) {
    const payload = { ...get(xpubToDelete)! };
    set(xpubToDelete, null);
    await deleteXpub(payload);
    get(balanceTable)?.removeCollapsed(payload);

    startPromise(refreshAccounts(blockchain));
  }
};

const cancelDelete = () => {
  set(confirmDelete, false);
  set(xpubToDelete, null);
};
</script>
