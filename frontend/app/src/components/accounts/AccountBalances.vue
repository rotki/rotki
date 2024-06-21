<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import type { BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

const props = withDefaults(
  defineProps<{
    balances: BlockchainAccountWithBalance[];
    blockchain: string;
    title: string;
    loopring?: boolean;
  }>(),
  {
    loopring: false,
  },
);

const emit = defineEmits<{
  (e: 'edit-account', account: BlockchainAccountWithBalance): void;
}>();

const { t } = useI18n();

const { blockchain, loopring } = toRefs(props);

const selectedAddresses = ref<string[]>([]);
const visibleTags = ref<string[]>([]);
const editedAccount = ref<BlockchainAccountWithBalance>();

const { isTaskRunning } = useTaskStore();
const { handleBlockchainRefresh } = useRefresh();
const { detectingTokens } = useTokenDetection(blockchain);
const { getChainName, supportsTransactions } = useSupportedChains();

const isEth2 = computed<boolean>(() => get(blockchain) === Blockchain.ETH2);
const hasTokenDetection = computed<boolean>(() => supportsTransactions(get(blockchain)));
const chainName = computed(() => get(getChainName(blockchain)));

const isQueryingBlockchain = isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);

const isAnyBalancesFetching = computed<boolean>(() => {
  if (!get(isEth2))
    return get(isQueryingBlockchain);

  const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);

  return get(isQueryingBlockchain) || get(isLoopringLoading);
});

const operationRunning = computed<boolean>(
  () => get(isTaskRunning(TaskType.ADD_ACCOUNT)) || get(isTaskRunning(TaskType.REMOVE_ACCOUNT)),
);

const { isLoading } = useStatusStore();
const isSectionLoading = computed<boolean>(() => {
  const section = get(loopring) ? 'loopring' : get(blockchain);
  return get(isLoading(Section.BLOCKCHAIN, section));
});

const selection = computed<BlockchainAccountWithBalance[]>(() => props.balances.filter(account => get(selectedAddresses).includes(getAccountId(account))));

function editAccount(account: BlockchainAccountWithBalance) {
  set(editedAccount, account);
  emit('edit-account', account);
}

const { fetchAccounts } = useBlockchains();
const { showConfirmation } = useAccountDelete();

async function refreshClick() {
  await fetchAccounts(get(blockchain), true);
  await handleBlockchainRefresh(blockchain);
}

const { massDetecting } = storeToRefs(useBlockchainTokensStore());
const isMassDetecting = computed(() => {
  const massDetectingVal = get(massDetecting);
  if (!massDetectingVal)
    return false;

  return [get(blockchain), 'all'].includes(massDetectingVal);
});

const refreshDisabled = logicOr(isSectionLoading, detectingTokens);
</script>

<template>
  <RuiCard>
    <template #header>
      <div class="flex flex-row items-center gap-2">
        <SummaryCardRefreshMenu
          data-cy="account-balances-refresh-menu"
          :disabled="refreshDisabled"
          :loading="isMassDetecting"
          :tooltip="
            t('account_balances.refresh_tooltip', {
              blockchain: chainName,
            })
          "
          @refresh="refreshClick()"
        >
          <template
            v-if="hasTokenDetection"
            #refreshMenu
          >
            <BlockchainBalanceRefreshBehaviourMenu />
          </template>
        </SummaryCardRefreshMenu>
        <CardTitle class="ml-2">
          {{ title }}
        </CardTitle>
      </div>
    </template>

    <div class="flex flex-col md:flex-row md:items-center gap-2">
      <div class="grow flex items-center gap-2">
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              data-cy="account-balances__delete-button"
              color="error"
              variant="outlined"
              :disabled="
                isAnyBalancesFetching || operationRunning || selectedAddresses.length === 0
              "
              @click="showConfirmation(selection)"
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
              :loading="isMassDetecting"
              :disabled="refreshDisabled"
              @click="handleBlockchainRefresh(blockchain, true)"
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
      class="mt-4"
      :loopring="loopring"
      :blockchain="blockchain"
      :balances="balances"
      :visible-tags="visibleTags"
      :selected.sync="selectedAddresses"
      @edit-click="editAccount($event)"
      @delete-xpub="showConfirmation([$event])"
    />
  </RuiCard>
</template>
