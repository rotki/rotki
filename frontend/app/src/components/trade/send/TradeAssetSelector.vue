<script setup lang="ts">
import type { TradableAsset } from '@/types/trade';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import TradeAssetDisplay from '@/components/trade/send/TradeAssetDisplay.vue';
import { useTradeAsset } from '@/composables/trade/asset';
import { useWalletHelper } from '@/composables/trade/wallet-helper';
import { getChainIdFromNamespace, tradableChains, useWalletStore } from '@/store/trade/wallet';
import { Blockchain } from '@rotki/common';

const asset = defineModel<string>({ required: true });
const chain = defineModel<string>('chain', { required: true });

const props = defineProps<{
  address?: string;
}>();

const emit = defineEmits(['set-max']);

const { address } = toRefs(props);
const { allOwnedAssets, getAssetDetail } = useTradeAsset(address);

const { connected, supportedChainIds } = storeToRefs(useWalletStore());
const { getChainFromChainId } = useWalletHelper();

const openDialog = ref(false);
const internalChain = ref<string>(Blockchain.ETH);

function getOwnedAssetsByChain(chain: string) {
  return get(allOwnedAssets).filter(item => item.chain === chain);
}

watchImmediate([asset, chain, allOwnedAssets], ([currentAsset, chain, _]) => {
  const ownedByChain = getOwnedAssetsByChain(chain);

  if (!ownedByChain.map(item => item.asset).includes(currentAsset) && ownedByChain.length > 0) {
    set(asset, ownedByChain[0].asset);
  }
});

watchImmediate(chain, (chain) => {
  set(internalChain, chain);
});

const assetDetail = getAssetDetail(asset, chain);

const chainOptions = computed(() => {
  const supportedChainIdsVal = get(supportedChainIds);
  if (supportedChainIdsVal.length === 0) {
    return [
      'evm',
      ...tradableChains,
    ];
  }

  const supportedChainsFromProvider = supportedChainIdsVal.map((item) => {
    const chainId = getChainIdFromNamespace(item);
    return getChainFromChainId(chainId);
  });

  const supportedChains = tradableChains.filter(item => supportedChainsFromProvider.includes(item));

  return [
    'evm',
    ...supportedChains,
  ];
});

const assetOptions = computed(() => {
  const chain = get(internalChain);
  const options = get(allOwnedAssets);
  if (chain === 'evm') {
    return options;
  }
  return options.filter(item => item.chain === chain);
});

async function selectAsset(item: TradableAsset) {
  set(asset, item.asset);
  set(chain, item.chain);
  set(openDialog, false);
}

function setMax() {
  emit('set-max');
}
</script>

<template>
  <div
    class="border border-default rounded-b-lg bg-rui-grey-50 px-3 py-2.5 mt-0.5 flex justify-between items-center hover:bg-rui-grey-100 cursor-pointer"
    @click="openDialog = true"
  >
    <TradeAssetDisplay
      v-if="assetDetail"
      :data="assetDetail"
    />
    <div class="flex items-center gap-2 text-rui-text-secondary">
      <RuiButton
        v-if="connected"
        class="rounded-full"
        size="sm"
        color="primary"
        @click.stop="setMax()"
      >
        Max
      </RuiButton>
      <RuiIcon
        name="lu-chevron-down"
        size="20"
      />
    </div>
  </div>
  <RuiDialog
    v-model="openDialog"
    max-width="500"
  >
    <RuiCard
      divide
      no-padding
      content-class="overflow-hidden"
    >
      <template #header>
        Select a token
      </template>
      <div class="p-4 pb-2">
        <ChainSelect
          v-model="internalChain"
          class="mb-2"
          hide-details
          dense
          :items="chainOptions"
        />
      </div>
      <div class="flex flex-col max-h-[calc(100vh-400px)] overflow-auto py-2">
        <TradeAssetDisplay
          v-for="item in assetOptions"
          :key="item.asset"
          list
          class="hover:bg-rui-grey-100 cursor-pointer py-2 px-4"
          :data="item"
          @click="selectAsset(item)"
        />
      </div>
    </RuiCard>
  </RuiDialog>
</template>
