<template>
  <v-dialog v-model="details" scrollable max-width="450px">
    <template #activator="{ on, attrs }">
      <v-tooltip open-delay="400" top>
        <template #activator="{ on: tipOn, attrs: tipAttrs }">
          <v-btn
            icon
            small
            v-bind="{ ...tipAttrs, ...attrs }"
            v-on="{ ...on, ...tipOn }"
          >
            <v-icon small color="primary">mdi-launch</v-icon>
          </v-btn>
        </template>
        <span>{{ $t('uniswap_pool_details.tooltip') }}</span>
      </v-tooltip>
    </template>
    <card>
      <template #title>{{ $t('uniswap_pool_details.title') }}</template>
      <v-row v-for="token in balance.assets" :key="token.asset" align="center">
        <v-col cols="auto">
          <asset-icon :identifier="token.asset" size="24px" class="mr-1" />
        </v-col>
        <v-col>
          <v-row no-gutters>
            <v-col class="font-weight-medium">
              {{ $t('uniswap_pool_details.asset_liquidity') }}
            </v-col>
            <v-col cols="auto">
              <amount-display
                class="ps-4"
                :asset="token.asset"
                :value="token.totalAmount"
              />
            </v-col>
          </v-row>
          <v-row no-gutters>
            <v-col class="font-weight-medium">
              {{ $t('uniswap_pool_details.price') }}
            </v-col>
            <v-col cols="auto">
              <amount-display
                class="ps-4"
                show-currency="symbol"
                fiat-currency="USD"
                :value="token.usdPrice"
              />
            </v-col>
          </v-row>
        </v-col>
      </v-row>
      <v-row v-if="balance.totalSupply">
        <v-col class="font-weight-medium">
          {{ $t('uniswap_pool_details.liquidity') }}
        </v-col>
        <v-col cols="auto">
          <amount-display :value="balance.totalSupply" />
        </v-col>
      </v-row>
    </card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import AssetMixin from '@/mixins/asset-mixin';
import { UniswapBalance } from '@/store/defi/types';

@Component({
  name: 'UniswapPoolDetails'
})
export default class UniswapPoolDetails extends Mixins(AssetMixin) {
  details: boolean = false;
  @Prop({ required: true })
  balance!: UniswapBalance;
}
</script>

<style scoped lang="scss"></style>
