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
const { refreshAccounts, fetchAccounts } = useBlockchains();
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

const refreshClick = async () => {
  await fetchAccounts(get(blockchain), true);
  await handleBlockchainRefresh();
};
</script>

<template>
  <RuiCard
    :id="`blockchain-balances-${blockchain}`"
    data-cy="account-balances"
    :data-location="blockchain"
  >
    <template #header>
      <div class="flex flex-row items-center gap-2">
        <SummaryCardRefreshMenu
          data-cy="account-balances-refresh-menu"
          :loading="isSectionLoading || detectingTokens"
          :tooltip="
            t('account_balances.refresh_tooltip', {
              blockchain: chainName
            })
          "
          @refresh="refreshClick()"
        >
          <template v-if="hasTokenDetection" #refreshMenu>
            <BlockchainBalanceRefreshBehaviourMenu />
          </template>
        </SummaryCardRefreshMenu>
        <CardTitle class="ml-2">{{ title }}</CardTitle>
      </div>
    </template>

    <div class="flex flex-col md:flex-row md:items-center gap-2">
      <div class="grow flex items-center gap-2">
        <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
          <template #activator>
            <RuiButton
              data-cy="account-balances__delete-button"
              color="error"
              variant="outlined"
              :disabled="
                isAnyBalancesFetching ||
                operationRunning ||
                selectedAddresses.length === 0
              "
              @click="showConfirmation(selectedAddresses)"
            >
              <template #prepend>
                <RuiIcon name="delete-bin-line" />
              </template>
              {{ t('common.actions.delete') }}
            </RuiButton>
          </template>
          {{ t('account_balances.delete_tooltip') }}
        </RuiTooltip>

        <RuiTooltip
          v-if="hasTokenDetection"
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              class="ml-2"
              variant="outlined"
              color="primary"
              :loading="detectingTokens"
              :disabled="detectingTokens || isSectionLoading"
              @click="detectTokensOfAllAddresses()"
            >
              <template #prepend>
                <RuiIcon name="refresh-line" />
              </template>

              {{ t('account_balances.detect_tokens.tooltip.redetect') }}
            </RuiButton>
          </template>
          {{ t('account_balances.detect_tokens.tooltip.redetect_all') }}
        </RuiTooltip>
      </div>
      <TagFilter
        v-if="!isEth2"
        v-model="visibleTags"
        class="max-w-[360px]"
        hide-details
      />
    </div>

    <AccountBalanceTable
      ref="balanceTable"
      class="mt-4"
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
  </RuiCard>
</template>
