<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { TaskType } from '@/types/task-type';
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

const { t } = useI18n();

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
const { getChainName, supportsTransactions } = useSupportedChains();

const isEth2 = computed<boolean>(() => get(blockchain) === Blockchain.ETH2);

const hasTokenDetection = computed<boolean>(() =>
  supportsTransactions(get(blockchain))
);

const chainName = computed(() => get(getChainName(blockchain)));

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
    message = t('account_balances.confirm_delete.description_address', {
      count: payload.length
    });
  } else {
    message = t('account_balances.confirm_delete.description_xpub', {
      address: payload.xpub
    });
  }
  show(
    {
      title: t('account_balances.confirm_delete.title'),
      message
    },
    async () => deleteAccount(payload)
  );
};
</script>

<template>
  <VCard :class="`${blockchain.toLocaleLowerCase()}-account-balances`">
    <VCardTitle>
      <VRow align="center" no-gutters>
        <VCol cols="auto">
          <RefreshButton
            class="account-balances__refresh"
            :loading="isSectionLoading || detectingTokens"
            :tooltip="
              t('account_balances.refresh_tooltip', {
                blockchain: chainName
              })
            "
            @refresh="handleBlockchainRefresh()"
          />
        </VCol>
        <VCol cols="auto">
          <SummaryCardRefreshMenu v-if="hasTokenDetection">
            <template #refreshMenu>
              <BlockchainBalanceRefreshBehaviourMenu />
            </template>
          </SummaryCardRefreshMenu>
        </VCol>
        <VCol class="ps-2">
          <CardTitle>{{ title }}</CardTitle>
        </VCol>
      </VRow>
    </VCardTitle>
    <VCardText>
      <VRow class="mb-2">
        <VCol cols="12" sm="6">
          <VTooltip top>
            <template #activator="{ on, attrs }">
              <span v-bind="attrs" v-on="on">
                <VBtn
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
                  <VIcon> mdi-delete-outline </VIcon>
                  <span>{{ t('common.actions.delete') }}</span>
                </VBtn>
              </span>
            </template>
            <span>{{ t('account_balances.delete_tooltip') }}</span>
          </VTooltip>
          <VTooltip v-if="hasTokenDetection" top>
            <template #activator="{ on }">
              <VBtn
                class="ml-2"
                text
                outlined
                :loading="detectingTokens"
                :disabled="detectingTokens || isSectionLoading"
                v-on="on"
                @click="detectTokensOfAllAddresses()"
              >
                <VIcon class="mr-2">mdi-refresh</VIcon>
                {{ t('account_balances.detect_tokens.tooltip.redetect') }}
              </VBtn>
            </template>
            <span>
              {{ t('account_balances.detect_tokens.tooltip.redetect_all') }}
            </span>
          </VTooltip>
        </VCol>
        <VCol v-if="!isEth2" cols="12" sm="6">
          <TagFilter v-model="visibleTags" hide-details />
        </VCol>
      </VRow>

      <AccountBalanceTable
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
    </VCardText>
  </VCard>
</template>
