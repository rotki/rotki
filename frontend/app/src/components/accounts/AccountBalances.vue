<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { TaskType } from '@/types/task-type';
import { startPromise } from '@/utils';
import { isTokenChain } from '@/types/blockchain/chains';
import {
  type AccountWithBalance,
  type BlockchainAccountWithBalance,
  type XpubPayload
} from '@/types/blockchain/accounts';

const props = withDefaults(
  defineProps<{
    balances: AccountWithBalance[];
    blockchain: Blockchain;
    title: string;
    loopring?: boolean;
  }>(),
  {
    loopring: false
  }
);

const emit = defineEmits<{
  (e: 'edit-account', account: BlockchainAccountWithBalance): void;
}>();

const { blockchain } = toRefs(props);

const selectedAddresses = ref<string[]>([]);
const visibleTags = ref<string[]>([]);
const editedAccount = ref<string>('');
const balanceTable = ref<any>(null);

const { isTaskRunning } = useTaskStore();
const { refreshBlockchainBalances } = useRefresh(blockchain);
const { detectTokensOfAllAddresses, detectingTokens } =
  useTokenDetection(blockchain);
const { show } = useConfirmStore();

const redetectAllTokens = async () => {
  await detectTokensOfAllAddresses();
};

const { tc } = useI18n();

const isEth2 = computed<boolean>(() => {
  return get(blockchain) === Blockchain.ETH2;
});

const hasTokenDetection = computed<boolean>(() =>
  isTokenChain(get(blockchain))
);

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

const editAccount = (account: BlockchainAccountWithBalance) => {
  set(editedAccount, account.address);
  emit('edit-account', account);
};

const { deleteEth2Validators } = useEthAccountsStore();
const { removeAccount } = useBlockchainAccountsStore();
const { refreshAccounts } = useBlockchainStore();
const { deleteXpub } = useBtcAccountsStore();

const deleteAccount = async (payload: XpubPayload | string[]) => {
  if (Array.isArray(payload)) {
    if (payload.length === 0) {
      return;
    }

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
  } else {
    await deleteXpub(payload);
    get(balanceTable)?.removeCollapsed(payload);

    startPromise(refreshAccounts(blockchain));
  }
};

const showConfirmation = (payload: XpubPayload | string[]) => {
  let message: string;
  if (Array.isArray(payload)) {
    message = tc('account_balances.confirm_delete.description_address', 0, {
      count: payload.length
    });
  } else {
    message = tc('account_balances.confirm_delete.description_xpub', 0, {
      address: payload.xpub
    });
  }
  show(
    {
      title: tc('account_balances.confirm_delete.title'),
      message
    },
    async () => deleteAccount(payload)
  );
};
</script>

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
                  @click="showConfirmation(selectedAddresses)"
                >
                  <v-icon> mdi-delete-outline </v-icon>
                  <span>{{ tc('common.actions.delete') }}</span>
                </v-btn>
              </span>
            </template>
            <span>{{ tc('account_balances.delete_tooltip') }}</span>
          </v-tooltip>
          <v-tooltip v-if="hasTokenDetection" top>
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
        @delete-xpub="showConfirmation($event)"
        @addresses-selected="selectedAddresses = $event"
      />
    </v-card-text>
  </v-card>
</template>
