<script lang="ts" setup>
import UniswapPoolHeader from '@/components/defi/uniswap/UniswapPoolHeader.vue';
import UniswapPoolAssetBalance from '@/components/defi/uniswap/UniswapPoolAssetBalance.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import type { LpType, XswapBalance } from '@rotki/common';

defineProps<{
  item: XswapBalance;
  lpType: LpType;
}>();

const { t } = useI18n();
</script>

<template>
  <RuiCard>
    <UniswapPoolHeader
      :item="item"
      :lp-type="lpType"
    />

    <div class="flex flex-col gap-4">
      <div>
        <div class="text-rui-text-secondary text-body-2">
          {{ t('common.balance') }}
        </div>
        <BalanceDisplay
          class="flex text-h6 !leading-7"
          :value="item.userBalance"
          align="start"
          no-icon
        />
      </div>

      <div>
        <div class="text-rui-text-secondary text-body-2">
          {{ t('common.assets') }}
        </div>
        <UniswapPoolAssetBalance
          v-for="asset in item.assets"
          :key="`${asset.asset}-${item.address}-balances`"
          :asset="asset"
        />
      </div>
    </div>
  </RuiCard>
</template>
