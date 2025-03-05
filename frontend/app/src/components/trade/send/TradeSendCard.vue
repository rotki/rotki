<script setup lang="ts">
import type BigNumber from 'bignumber.js';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import TradeAmountInput from '@/components/trade/send/TradeAmountInput.vue';
import TradeAssetSelector from '@/components/trade/send/TradeAssetSelector.vue';
import { useWalletHelper } from '@/composables/trade/wallet-helper';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useBlockchainStore } from '@/store/blockchain';
import { useWalletStore } from '@/store/trade/wallet';
import { CURRENCY_USD } from '@/types/currencies';
import { bigNumberSum } from '@/utils/calculation';
import { bigNumberify, Blockchain, isValidEthAddress, Zero } from '@rotki/common';

const { getChainFromChainId, getChainIdFromChain } = useWalletHelper();

const walletStore = useWalletStore();
const { connected, connectedAddress, connectedChainId } = storeToRefs(walletStore);
const { disconnect, open, switchNetwork } = walletStore;

const blockchainStore = useBlockchainStore();
const { addresses, blockchainAccounts } = storeToRefs(blockchainStore);
const { blockchainAccountList } = blockchainStore;

const amount = ref('');
const asset = ref('ETH');
const desiredChain = ref(Blockchain.ETH);
const toAddress = ref('');

const tradeAmountInput = useTemplateRef<InstanceType<typeof TradeAmountInput>>('tradeAmountInput');

watch(connectedChainId, (curr, prev) => {
  if (!isDefined(curr) || curr === prev) {
    return;
  }

  set(desiredChain, getChainFromChainId(curr));
});

const wrongNetwork = computed(() => {
  const chainId = get(connectedChainId);
  if (!get(connected) || !chainId) {
    return false;
  }
  const chainIdOfConnectedNetwork = getChainFromChainId(chainId);
  return get(desiredChain) !== chainIdOfConnectedNetwork;
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

  const accounts = blockchainAccountList(get(blockchainAccounts)).filter(account => account.groupId === get(connectedAddress));

  const usdValues = accounts.map(item => item.usdValue);
  return bigNumberSum(usdValues);
});

const valid = computed<boolean>(() => {
  const amountToBigNumber = bigNumberify(get(amount));
  const to = get(toAddress);

  const amountValid = !amountToBigNumber.isNaN() && amountToBigNumber.gt(0);
  const toAddressValid = !!to && isValidEthAddress(to);

  return amountValid && toAddressValid;
});

function switchToDesireNetwork() {
  const chainId = getChainIdFromChain(get(desiredChain));
  switchNetwork(chainId);
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
  get(tradeAmountInput)?.setMax();
}

function send() {
 //
}
</script>

<template>
  <RuiCard
    class="!rounded-xl"
    no-padding
  >
    <div class="p-6 flex flex-col gap-6 border-b">
      <RuiAlert
        v-if="connected && !addressTracked"
        type="warning"
      >
        This wallet address is not tracked in rotki, so you can't see your tokens.
        <RuiButton
          color="primary"
          size="sm"
          class="mt-2"
          @click="trackAddress()"
        >
          Track address
        </RuiButton>
      </RuiAlert>
      <div class="flex justify-between items-center">
        <div class="min-h-[2.75rem]">
          <template v-if="connected">
            <div class="text-rui-text-secondary text-sm">
              Available Balance
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
        <div>
          <RuiButton
            v-if="!connected"
            color="primary"
            class="!py-2"
            @click="open()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-wallet"
                size="18"
              />
            </template>
            Connect Wallet
          </RuiButton>

          <RuiMenu
            v-else-if="connectedAddress"
            full-width
            class="flex"
          >
            <template #activator="{ attrs }">
              <div
                v-bind="attrs"
                class="border border-default rounded-md px-2 py-1 flex items-center gap-2 font-mono text-sm font-medium cursor-pointer"
              >
                <div class="p-0.5 rounded-full size-3 border border-rui-success-lighter/40">
                  <div class="size-full rounded-full bg-rui-success-lighter" />
                </div>
                <HashLink
                  :text="connectedAddress"
                  copy-only
                />
              </div>
            </template>
            <template #default="{ width }">
              <div
                class="py-1"
                :style="{ width: `${width}px` }"
              >
                <RuiButton
                  variant="list"
                  size="sm"
                  @click="open()"
                >
                  Open
                </RuiButton>
                <RuiButton
                  variant="list"
                  size="sm"
                  @click="disconnect()"
                >
                  <template #prepend>
                    <RuiIcon
                      name="lu-log-out"
                      size="14"
                    />
                  </template>
                  Disconnect
                </RuiButton>
              </div>
            </template>
          </RuiMenu>
        </div>
      </div>
    </div>
    <div class="p-6">
      <div class="border border-default rounded-t-lg bg-rui-grey-50 p-3">
        <div class="text-rui-grey-500 text-sm font-medium">
          I'm sending
        </div>
        <TradeAmountInput
          ref="tradeAmountInput"
          v-model="amount"
          :chain="desiredChain"
          :address="addressTracked ? connectedAddress : undefined"
          :asset="asset"
        />
      </div>
      <TradeAssetSelector
        v-model="asset"
        v-model:chain="desiredChain"
        :address="addressTracked ? connectedAddress : undefined"
        @set-max="setMax()"
      />
      <label class="p-3 bg-rui-grey-50 rounded-lg border border-default mt-1 block">
        <span class="text-sm text-rui-grey-500 font-medium">
          To address
        </span>
        <input
          v-model="toAddress"
          type="text"
          class="outline-none w-full bg-transparent text-sm"
          placeholder="E.g. 0x9531c059098e3d194ff87febb587ab07b30b1306"
        />
      </label>
    </div>
    <div class="p-6 border-t border-default">
      <RuiButton
        v-if="!addressTracked"
        color="primary"
        size="lg"
        class="!w-full"
        @click="trackAddress()"
      >
        Track Address
      </RuiButton>
      <RuiButton
        v-else-if="wrongNetwork"
        color="primary"
        size="lg"
        class="!w-full"
        @click="switchToDesireNetwork()"
      >
        Change Network
      </RuiButton>
      <RuiButton
        v-else
        color="primary"
        size="lg"
        class="!w-full"
        :disabled="!valid"
        @click="send()"
      >
        Send
      </RuiButton>
    </div>
  </RuiCard>
</template>
