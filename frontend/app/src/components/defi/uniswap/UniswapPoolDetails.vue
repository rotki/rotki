<script setup lang="ts">
import { Zero } from '@/utils/bignumbers';
import type {
  XswapAsset,
  XswapBalance,
} from '@rotki/common/lib/defi/xswap';

defineProps<{
  balance: XswapBalance;
}>();

const details = ref<boolean>(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

function getTotal({ totalAmount, usdPrice }: XswapAsset) {
  return usdPrice.multipliedBy(totalAmount ?? One);
}
</script>

<template>
  <RuiDialog
    v-model="details"
    max-width="450px"
  >
    <template #activator="{ on }">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            color="primary"
            icon
            v-on="on"
          >
            <RuiIcon name="external-link-line" />
          </RuiButton>
        </template>
        <span>{{ t('liquidity_pool_details.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <RuiCard>
      <template #header>
        {{ t('liquidity_pool_details.title') }}
      </template>
      <template v-for="(token, key) in balance.assets">
        <RuiDivider
          v-if="key > 0"
          :key="`${token.asset}divider`"
          class="my-3"
        />
        <div
          :key="token.asset"
          class="flex items-center gap-4"
        >
          <AssetIcon
            :identifier="token.asset"
            size="24px"
          />
          <div class="flex-1">
            <div class="text-rui-text-secondary text-body-2">
              {{ t('liquidity_pool_details.total_amount') }}
            </div>
            <AmountDisplay
              class="font-bold"
              :asset="token.asset"
              :value="token.totalAmount ?? Zero"
            />
          </div>
          <div class="flex-1">
            <div class="text-rui-text-secondary text-body-2">
              {{
                t('liquidity_pool_details.total_value_in_symbol', {
                  symbol: currencySymbol,
                })
              }}
            </div>
            <AmountDisplay
              class="font-bold"
              fiat-currency="USD"
              :value="getTotal(token)"
            />
          </div>
        </div>
      </template>
      <div
        v-if="balance.totalSupply"
        class="flex gap-2 items-center pt-6"
      >
        <div class="text-rui-text-secondary text-body-2">
          {{ t('liquidity_pool_details.liquidity') }}:
        </div>
        <AmountDisplay
          class="font-bold"
          :value="balance.totalSupply"
        />
      </div>
    </RuiCard>
  </RuiDialog>
</template>
