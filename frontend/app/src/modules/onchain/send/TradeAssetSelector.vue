<script setup lang="ts">
import type { TradableAsset } from '@/modules/onchain/types';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import TradeAssetDisplay from '@/modules/onchain/send/TradeAssetDisplay.vue';
import { useBalanceQueries } from '@/modules/onchain/send/use-balance-queries';
import { useTradableAsset } from '@/modules/onchain/use-tradable-asset';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { type BigNumber, Blockchain } from '@rotki/common';

const asset = defineModel<string>({ required: true });
const chain = defineModel<string>('chain', { required: true });

const props = defineProps<{
  address?: string;
  amount: BigNumber | undefined;
}>();

const emit = defineEmits<{
  'set-max': [];
  'refresh': [];
}>();

const { address } = toRefs(props);

const openDialog = ref(false);
const internalChain = ref<string>(Blockchain.ETH);

const { t } = useI18n({ useScope: 'global' });

const { allOwnedAssets, getAssetDetail } = useTradableAsset(address);

const { connected, connectedAddress, supportedChainsForConnectedAccount } = storeToRefs(useWalletStore());
const { useQueryingBalances } = useBalanceQueries(connected, connectedAddress);

const assetDetail = getAssetDetail(asset, chain);

const chainOptions = computed(() => [
  'evm',
  ...get(supportedChainsForConnectedAccount),
]);

const assetOptions = computed(() => {
  const chain = get(internalChain);
  const options = get(allOwnedAssets);
  if (chain === 'evm') {
    return options.filter(item => get(supportedChainsForConnectedAccount).includes(item.chain));
  }
  return options.filter(item => item.chain === chain);
});

function getOwnedAssetsByChain(chain: string) {
  return get(allOwnedAssets).filter(item => item.chain === chain);
}

async function selectAsset(item: TradableAsset) {
  set(asset, item.asset);
  set(chain, item.chain);
  set(openDialog, false);
}

function setMax() {
  emit('set-max');
}

watchImmediate([asset, chain, allOwnedAssets], ([currentAsset, chain, _]) => {
  const ownedByChain = getOwnedAssetsByChain(chain);

  if (!ownedByChain.map(item => item.asset).includes(currentAsset) && ownedByChain.length > 0) {
    set(asset, ownedByChain[0].asset || '');
  }
});

watchImmediate([address, chain], ([_, currentChain]) => {
  const owned = get(allOwnedAssets);
  if (currentChain) {
    const filteredByChain = owned.filter(item => item.chain === currentChain);
    if (filteredByChain.length > 0) {
      set(asset, filteredByChain[0].asset);
      return;
    }
  }

  const mostBalance = owned[0];
  if (mostBalance) {
    set(asset, mostBalance.asset);
    set(chain, mostBalance.chain);
  }
});

watchImmediate(chain, (chain) => {
  set(internalChain, chain);
});
</script>

<template>
  <div
    class="border border-default rounded-b-lg bg-rui-grey-50 dark:bg-rui-grey-900 px-3 py-2.5 mt-0.5 flex justify-between items-center hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800 cursor-pointer gap-4"
    @click="openDialog = true"
  >
    <TradeAssetDisplay
      v-if="asset && assetDetail"
      :key="asset + chain"
      class="py-2 -my-2 flex-1 overflow-hidden"
      :data="assetDetail"
      :amount="amount"
      @refresh="emit('refresh')"
    />
    <div
      v-else
      class="h-9 text-rui-text-secondary flex items-center"
    >
      {{ t('trade.select_asset.title') }}
    </div>
    <div class="flex items-center gap-2 text-rui-text-secondary">
      <RuiButton
        v-if="connected"
        class="rounded-full"
        size="sm"
        color="primary"
        @click.stop="setMax()"
      >
        {{ t('trade.select_asset.max') }}
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
        {{ t('trade.select_asset.select_token') }}
      </template>
      <RuiButton
        variant="text"
        class="absolute top-2 right-2"
        icon
        @click="openDialog = false"
      >
        <RuiIcon
          class="text-white"
          name="lu-x"
        />
      </RuiButton>
      <div class="p-4 pb-4">
        <RuiAlert
          v-if="useQueryingBalances"
          class="mb-4"
          type="warning"
        >
          {{ t('trade.warning.query_on_progress') }}
        </RuiAlert>
        <ChainSelect
          v-model="internalChain"
          hide-details
          dense
          :items="chainOptions"
        />
      </div>
      <div
        v-if="assetOptions.length > 0"
        class="flex flex-col max-h-[calc(100vh-400px)] overflow-auto pb-2"
      >
        <TradeAssetDisplay
          v-for="item in assetOptions"
          :key="item.asset + item.chain"
          list
          class="hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800 cursor-pointer py-2 px-4"
          :data="item"
          @click="selectAsset(item)"
        />
      </div>
      <div
        v-else
        class="pb-4 px-4 text-rui-text-secondary"
      >
        {{ t('trade.select_asset.no_assets_found') }}
      </div>
    </RuiCard>
  </RuiDialog>
</template>
