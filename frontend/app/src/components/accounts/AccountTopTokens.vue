<script lang="ts" setup>
import type { BlockchainAccountGroupWithBalance, BlockchainAccountWithBalance } from '@/types/blockchain/accounts';
import type { AssetBalance } from '@rotki/common';

const props = defineProps<{
  row: BlockchainAccountWithBalance | BlockchainAccountGroupWithBalance;
  loading: boolean;
}>();

const chains = computed<string[]>(() => {
  const row = props.row;
  return 'chains' in row ? row.chains : [row.chain];
});

const { getAccountDetails } = useBlockchainStore();
const { assetInfo } = useAssetInfoRetrieval();

const assets = computed<AssetBalance[]>(() => {
  const address = getAccountAddress(props.row);

  const assets: Record<string, AssetBalance> = {};

  get(chains).forEach((chain) => {
    const details = getAccountDetails(chain, address);
    details.assets.forEach((item) => {
      const assetId = item.asset;
      const info = get(assetInfo(assetId));
      const key = info?.collectionId ? `collection-${info.collectionId}` : assetId;

      if (assets[key]) {
        assets[key] = {
          ...assets[key],
          ...balanceSum(assets[key], item),
        };
      }
      else {
        assets[key] = item;
      }
    });
  });

  return Object.values(assets)
    .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
});

const showMore = computed(() => get(assets).length - 3);
</script>

<template>
  <div class="flex justify-end pl-2">
    <template
      v-if="assets.length > 1"
    >
      <template
        v-for="asset in assets.slice(0, 3)"
        :key="asset.asset"
      >
        <RuiTooltip
          :close-delay="0"
          tooltip-class="!-ml-1"
        >
          <template #activator>
            <div
              data-cy="top-asset"
              class="rounded-full w-8 h-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 cursor-pointer overflow-hidden"
            >
              <AssetIcon
                no-tooltip
                flat
                :identifier="asset.asset"
                size="24px"
                class="[&_.icon-bg>div]:!rounded-full [&_.icon-bg>div]:!overflow-hidden"
                :show-chain="false"
              />
            </div>
          </template>

          <AmountDisplay
            :value="asset.amount"
            :asset="asset.asset"
            :asset-padding="0.1"
            data-cy="top-asset-amount"
          />
        </RuiTooltip>
      </template>
    </template>
    <AmountDisplay
      v-else-if="assets.length === 1"
      :value="assets[0].amount"
      :asset="assets[0].asset"
      :asset-padding="0.1"
    />
    <AmountDisplay
      v-else-if="(row.nativeAsset && row.amount) || loading"
      :value="row.amount"
      :asset="row.nativeAsset"
      :loading="loading"
      :asset-padding="0.1"
    />

    <div
      v-if="showMore > 0"
      class="rounded-full h-8 px-1 min-w-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 font-bold text-xs text-rui-light-text z-[1]"
    >
      {{ showMore }}+
    </div>
  </div>
</template>
