<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { TaskType } from '@/types/task-type';
import { isTokenChain } from '@/types/blockchain/chains';
import {
  type AccountWithBalance,
  type BlockchainAccountWithBalance,
  type XpubPayload
} from '@/types/blockchain/accounts';
import { Section } from '@/types/status';
import { chainSection } from '@/types/blockchain';

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

const { blockchain, loopring } = toRefs(props);

const selectedAddresses = ref<string[]>([]);
const visibleTags = ref<string[]>([]);
const editedAccount = ref<string>('');
const balanceTable = ref<any>(null);

const { isTaskRunning } = useTaskStore();
const { handleBlockchainRefresh } = useRefresh(blockchain);
const { detectTokensOfAllAddresses, detectingTokens } =
  useTokenDetection(blockchain);
const { show } = useConfirmStore();

const { tc } = useI18n();

const isEth2 = computed<boolean>(() => get(blockchain) === Blockchain.ETH2);

const hasTokenDetection = computed<boolean>(() =>
  isTokenChain(get(blockchain))
);

const isQueryingBlockchain = isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);

const isAnyBalancesFetching = computed<boolean>(() => {
  if (!get(isEth2)) {
    return get(isQueryingBlockchain);
  }
  const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);

  return get(isQueryingBlockchain) || get(isLoopringLoading);
});

const operationRunning = computed<boolean>(
  () =>
    get(isTaskRunning(TaskType.ADD_ACCOUNT)) ||
    get(isTaskRunning(TaskType.REMOVE_ACCOUNT))
);

const section = computed<Section>(() =>
  get(loopring) ? Section.L2_LOOPRING_BALANCES : chainSection[get(blockchain)]
);

const { isLoading } = useStatusStore();
const isSectionLoading = isLoading(get(section));

const editAccount = (account: BlockchainAccountWithBalance) => {
  set(editedAccount, account.address);
  emit('edit-account', account);
};

const { deleteEth2Validators } = useEthAccountsStore();
const { removeAccount } = useBlockchainAccounts();
const { refreshAccounts } = useBlockchains();
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
            :loading="isSectionLoading || detectingTokens"
            :tooltip="tc('account_balances.refresh_tooltip', 0, { blockchain })"
            @refresh="handleBlockchainRefresh"
          />
        </v-col>
        <v-col cols="auto">
          <summary-card-refresh-menu v-if="hasTokenDetection">
            <template #refreshMenu>
              <blockchain-balance-refresh-behaviour-menu />
            </template>
          </summary-card-refresh-menu>
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
                    isAnyBalancesFetching ||
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
                :disabled="detectingTokens || isSectionLoading"
                v-on="on"
                @click="detectTokensOfAllAddresses"
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
