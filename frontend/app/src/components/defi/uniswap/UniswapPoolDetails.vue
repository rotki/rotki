<script setup lang="ts">
import {
  type XswapAsset,
  type XswapBalance
} from '@rotki/common/lib/defi/xswap';
import { Zero } from '@/utils/bignumbers';

defineProps<{
  balance: XswapBalance;
}>();

const details = ref<boolean>(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const getTotal = ({ totalAmount, usdPrice }: XswapAsset) =>
  usdPrice.multipliedBy(totalAmount ?? One);
</script>

<template>
  <VDialog v-model="details" scrollable max-width="450px">
    <template #activator="{ on, attrs }">
      <VTooltip open-delay="400" top>
        <template #activator="{ on: tipOn, attrs: tipAttrs }">
          <VBtn
            icon
            small
            v-bind="{ ...tipAttrs, ...attrs }"
            v-on="{ ...on, ...tipOn }"
          >
            <VIcon small color="primary">mdi-launch</VIcon>
          </VBtn>
        </template>
        <span>{{ t('liquidity_pool_details.tooltip') }}</span>
      </VTooltip>
    </template>
    <Card>
      <template #title>{{ t('liquidity_pool_details.title') }}</template>
      <template v-for="(token, key) in balance.assets">
        <VDivider v-if="key > 0" :key="token.asset + 'divider'" class="my-3" />
        <VRow :key="token.asset" align="center">
          <VCol cols="auto" class="pr-2">
            <AssetIcon :identifier="token.asset" size="24px" />
          </VCol>
          <VCol>
            <VRow>
              <VCol md="6">
                <div class="text--secondary text-body-2">
                  {{ t('liquidity_pool_details.total_amount') }}
                </div>
                <div class="flex font-bold">
                  <AmountDisplay
                    :asset="token.asset"
                    :value="token.totalAmount ?? Zero"
                  />
                </div>
              </VCol>
              <VCol md="6">
                <div class="text--secondary text-body-2">
                  {{
                    t('liquidity_pool_details.total_value_in_symbol', {
                      symbol: currencySymbol
                    })
                  }}
                </div>
                <div class="flex font-bold">
                  <AmountDisplay fiat-currency="USD" :value="getTotal(token)" />
                </div>
              </VCol>
            </VRow>
          </VCol>
        </VRow>
      </template>
      <div v-if="balance.totalSupply" class="flex pt-6">
        <div class="text--secondary text-body-2">
          {{ t('liquidity_pool_details.liquidity') }}:
        </div>
        <div class="pl-2 font-bold">
          <AmountDisplay :value="balance.totalSupply" />
        </div>
      </div>
    </Card>
  </VDialog>
</template>
