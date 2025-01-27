<script setup lang="ts">
import type { GasFeeEstimation } from '@/types/trade';
import type BigNumber from 'bignumber.js';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import TradeAmountInput from '@/components/trade/send/TradeAmountInput.vue';
import TradeAssetSelector from '@/components/trade/send/TradeAssetSelector.vue';
import TradeConnectedAddressBadge from '@/components/trade/send/TradeConnectedAddressBadge.vue';
import TradeHistoryView from '@/components/trade/send/TradeHistoryView.vue';
import TradeRecipientAddress from '@/components/trade/send/TradeRecipientAddress.vue';
import { useTradeApi } from '@/composables/api/trade';
import { useSupportedChains } from '@/composables/info/chains';
import { useTradeAsset } from '@/composables/trade/asset';
import { useWalletHelper } from '@/composables/trade/wallet-helper';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useTaskStore } from '@/store/tasks';
import { useWalletStore } from '@/store/trade/wallet';
import { CURRENCY_USD } from '@/types/currencies';
import { TaskType } from '@/types/task-type';
import { bigNumberSum } from '@/utils/calculation';
import { logger } from '@/utils/logging';
import { bigNumberify, Blockchain, isValidEthAddress, Zero } from '@rotki/common';

const { t } = useI18n();

const amount = ref<string>('');
const asset = ref<string>('');
const assetChain = ref<string>(Blockchain.ETH);
const toAddress = ref<string>('');

const max = ref<string>('0');
const estimatingGas = ref<boolean>(false);
const showNeverInteractedWarning = ref<boolean>(false);
const errorMessage = ref<string>('');
const currentGasEstimationController = ref<AbortController | null>(null);

const { getChainFromChainId, getChainIdFromChain } = useWalletHelper();
const { getNativeAsset } = useSupportedChains();

const walletStore = useWalletStore();
const { connected, connectedAddress, connectedChainId, preparing, supportedChainsForConnectedAccount } = storeToRefs(walletStore);
const { getGasFeeForChain, open, sendTransaction, switchNetwork } = walletStore;

const { useIsTaskRunning } = useTaskStore();
const { balances } = storeToRefs(useBalancesStore());
const { accounts } = storeToRefs(useBlockchainAccountsStore());
const { addresses } = useAccountAddresses();
const { getAccountList } = useBlockchainAccountData();
const { getAssetDetail } = useTradeAsset(connectedAddress);
const { getIsInteractedBefore } = useTradeApi();

const queryingBalances = useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
const queryingBalancesDebounced = refDebounced(queryingBalances, 200);
const usedQueryingBalances = logicOr(queryingBalances, queryingBalancesDebounced);

function resetMax() {
  set(max, '0');
}

const isNativeAsset = computed(() => {
  const chain = get(assetChain);
  const assetVal = get(asset);
  if (!chain || !assetVal) {
    return false;
  }

  const native = getNativeAsset(chain);
  return assetVal === native;
});

watchImmediate([asset, assetChain, connectedChainId], async ([asset, chain, connectedChainId]) => {
  if (!get(connected) || !chain || !asset) {
    resetMax();
    return;
  }

  // Cancel previous request if it exists
  const controller = get(currentGasEstimationController);
  if (controller) {
    controller.abort();
  }

  const detail = get(getAssetDetail(asset, chain));

  if (!get(isNativeAsset)) {
    if (detail) {
      set(max, detail.amount.toFixed());
    }
    else {
      resetMax();
    }
    return;
  }

  try {
    if (getChainIdFromChain(chain) === connectedChainId) {
      // Create new controller for this request
      set(currentGasEstimationController, new AbortController());

      set(estimatingGas, true);

      const gasFeeEstimation = await Promise.race([
        getGasFeeForChain(),
        new Promise<GasFeeEstimation>((_, reject) => {
          get(currentGasEstimationController)?.signal.addEventListener('abort', () => {
            reject(new Error('Gas estimation cancelled'));
          });
        }),
      ]);

      // Only set max if the asset hasn't changed
      if (gasFeeEstimation) {
        const { maxAmount } = gasFeeEstimation;
        set(max, maxAmount);
        return;
      }
    }

    if (detail) {
      set(max, detail.amount.toFixed());
    }
    else {
      resetMax();
    }
  }
  catch (error: any) {
    if (error.message !== 'Gas estimation cancelled') {
      resetMax();
      logger.error(error);
    }
  }
  finally {
    set(currentGasEstimationController, null);
    set(estimatingGas, false);
  }
});

const tradeAmountInputRef = useTemplateRef<InstanceType<typeof TradeAmountInput>>('tradeAmountInputRef');

watchImmediate(connectedChainId, (curr, prev) => {
  if (!isDefined(curr) || curr === prev) {
    return;
  }

  set(assetChain, getChainFromChainId(curr));
});

const wrongNetwork = computed(() => {
  const chainId = get(connectedChainId);
  if (!get(connected) || !chainId) {
    return false;
  }
  const chainIdOfConnectedNetwork = getChainFromChainId(chainId);
  return get(assetChain) !== chainIdOfConnectedNetwork;
});

const addressTracked = computed(() => {
  const connectedVal = get(connected);
  const address = get(connectedAddress);

  if (!connectedVal || !address) {
    return false;
  }

  const accountsAddresses = [...new Set(Object.values(get(addresses)).flat())];
  return connectedVal && accountsAddresses.includes(address);
});

const availableBalance = computed<BigNumber>(() => {
  if (!get(addressTracked))
    return Zero;

  const filteredAccounts = getAccountList(get(accounts), get(balances)).filter(account => account.groupId === get(connectedAddress));

  const usdValues = filteredAccounts.map(item => item.usdValue);
  return bigNumberSum(usdValues);
});

const amountExceeded = computed(() => {
  const amountToBigNumber = bigNumberify(get(amount));
  const maxToBigNumber = bigNumberify(get(max));

  return amountToBigNumber.gt(maxToBigNumber);
});

const valid = computed<boolean>(() => {
  const amountToBigNumber = bigNumberify(get(amount));
  const to = get(toAddress);

  const amountValid = !amountToBigNumber.isNaN() && amountToBigNumber.gt(0);
  const toAddressValid = !!to && isValidEthAddress(to);

  return amountValid && toAddressValid && !get(amountExceeded);
});

function switchToDesireNetwork() {
  const chainId = getChainIdFromChain(get(assetChain));
  switchNetwork(BigInt(chainId));
}

const router = useRouter();

async function trackAddress() {
  await router.push(
    {
      path: '/accounts/evm/accounts',
      query: {
        add: 'true',
        addressToAdd: get(connectedAddress),
      },
    },
  );
}

function setMax() {
  get(tradeAmountInputRef)?.setMax();
}

async function send() {
  const isNative = get(isNativeAsset);
  const assetVal = get(asset);

  const params = {
    amount: get(amount),
    assetIdentifier: isNative ? undefined : assetVal,
    chain: get(assetChain),
    native: isNative,
    to: get(toAddress),
  };

  try {
    await sendTransaction(params);
  }
  catch (error) {
    set(errorMessage, error);
  }
}

watch([assetChain, supportedChainsForConnectedAccount], ([currentChain, chainOptions]) => {
  if (!chainOptions.includes(currentChain)) {
    set(assetChain, chainOptions[0]);
  }
});

watch([connectedAddress, toAddress], async ([fromAddress, toAddress]) => {
  if (!fromAddress || !toAddress) {
    return;
  }

  try {
    const result = await getIsInteractedBefore(fromAddress, toAddress);
    set(showNeverInteractedWarning, !result);
  }
  catch (error: any) {
    set(showNeverInteractedWarning, false);
    logger.error(error);
  }
});

watch([assetChain, asset], () => {
  set(amount, '');
});
</script>

<template>
  <RuiCard
    class="!rounded-xl"
    no-padding
  >
    <div class="p-6 flex flex-col gap-6 border-b border-default">
      <RuiAlert
        v-if="connected && !addressTracked"
        type="warning"
      >
        {{ t('trade.warning.not_tracked') }}
        <RuiButton
          color="primary"
          size="sm"
          class="mt-2"
          @click="trackAddress()"
        >
          {{ t('trade.actions.track') }}
        </RuiButton>
      </RuiAlert>
      <RuiAlert
        v-if="usedQueryingBalances"
        type="warning"
      >
        {{ t('trade.warning.query_on_progress') }}
      </RuiAlert>
      <div class="flex justify-between items-center">
        <div class="min-h-[2.75rem]">
          <template v-if="connected">
            <div class="text-rui-text-secondary text-sm">
              {{ t('trade.available_balances') }}
            </div>
            <div v-if="!addressTracked">
              -
            </div>
            <AmountDisplay
              v-else
              v-model="amount"
              :value="availableBalance"
              :fiat-currency="CURRENCY_USD"
              show-currency="symbol"
            />
          </template>
        </div>

        <div class="flex gap-2">
          <TradeConnectedAddressBadge />
          <TradeHistoryView />
        </div>
      </div>
    </div>
    <div class="p-6">
      <TradeAmountInput
        ref="tradeAmountInputRef"
        v-model="amount"
        :loading="estimatingGas"
        :max="max"
        :amount-exceeded="amountExceeded"
        :chain="assetChain"
        :address="addressTracked ? connectedAddress : undefined"
        :asset="asset"
      />
      <TradeAssetSelector
        v-model="asset"
        v-model:chain="assetChain"
        :address="addressTracked ? connectedAddress : undefined"
        @set-max="setMax()"
      />
      <TradeRecipientAddress
        v-model="toAddress"
        :chain="assetChain"
        :show-warning="showNeverInteractedWarning"
      />
    </div>
    <div class="p-6 border-t border-default">
      <RuiButton
        v-if="!connected"
        color="primary"
        size="lg"
        class="!w-full"
        @click="open()"
      >
        {{ t('trade.actions.connect_wallet') }}
      </RuiButton>
      <RuiButton
        v-else-if="!addressTracked"
        color="primary"
        size="lg"
        class="!w-full"
        @click="trackAddress()"
      >
        {{ t('trade.actions.track') }}
      </RuiButton>
      <RuiButton
        v-else-if="wrongNetwork"
        color="primary"
        size="lg"
        class="!w-full"
        @click="switchToDesireNetwork()"
      >
        {{ t('trade.actions.change_network') }}
      </RuiButton>
      <RuiButton
        v-else
        color="primary"
        size="lg"
        class="!w-full"
        :disabled="!valid || estimatingGas"
        :loading="preparing"
        @click="send()"
      >
        {{ t('trade.actions.send') }}
      </RuiButton>
    </div>
  </RuiCard>
  <RuiAlert
    v-if="errorMessage"
    type="error"
    class="whitespace-break-spaces mt-4 overflow-hidden [&>div:first-child]:overflow-hidden [&>div:first-child>div:last-child]:overflow-hidden"
    closeable
    @close="errorMessage = ''"
  >
    <div class="overflow-hidden">
      {{ errorMessage }}
    </div>
  </RuiAlert>
</template>
