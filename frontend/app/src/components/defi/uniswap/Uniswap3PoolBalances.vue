<script lang="ts" setup>
import { type XswapBalance } from '@rotki/common/lib/defi/xswap';
import { type LpType } from '@rotki/common/lib/defi';
import UniswapPoolHeader from '@/components/defi/uniswap/UniswapPoolHeader.vue';

defineProps<{
  item: XswapBalance;
  lpType: LpType;
}>();

const { t } = useI18n();

const premium = usePremium();
</script>

<template>
  <RuiCard>
    <UniswapPoolHeader :item="item" :lp-type="lpType" />

    <NftDetails v-if="item.nftId" :identifier="item.nftId" />

    <div class="flex flex-wrap">
      <div class="mt-6 mr-16">
        <div class="text-rui-text-secondary text-body-2">
          {{ t('common.balance') }}
        </div>
        <div class="flex text-h6">
          <AmountDisplay
            :value="item.userBalance.usdValue"
            fiat-currency="USD"
          />
        </div>
      </div>

      <div
        v-if="item.priceRange && item.priceRange.length > 0"
        class="mt-6 w-[50%]"
      >
        <div class="text-rui-text-secondary text-body-2">
          {{ t('uniswap.price_range') }}
        </div>
        <div class="flex text-h6">
          <AmountDisplay :value="item.priceRange[0]" fiat-currency="USD" />
          <div class="px-2">-</div>
          <AmountDisplay :value="item.priceRange[1]" fiat-currency="USD" />
        </div>
      </div>
    </div>

    <div class="mt-6">
      <div class="text-rui-text-secondary text-body-2">
        {{ t('common.assets') }}
      </div>
      <div v-if="premium">
        <UniswapPoolAssetBalance
          v-for="asset in item.assets"
          :key="`${asset.asset}-${item.address}-balances`"
          :asset="asset"
        />
      </div>

      <RuiCard v-else dense class="mt-4">
        <div class="flex items-center gap-2 text-body-2">
          <PremiumLock />
          {{ t('uniswap.assets_non_premium') }}
        </div>
      </RuiCard>
    </div>
  </RuiCard>
</template>
