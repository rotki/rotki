<template>
  <fragment>
    <div
      class="d-flex flex-row align-center justify-center liquidity__navigation"
    >
      <v-btn-toggle>
        <v-btn :to="UNISWAP" class="lp-navigation" text>
          <v-img
            contain
            width="24"
            height="24"
            class="me-2"
            :src="require('@/assets/images/defi/uniswap.svg')"
          />
          {{ $t('liquidity.uniswap') }}
        </v-btn>
        <v-btn :to="BALANCER" class="lp-navigation" text>
          <v-img
            contain
            width="24"
            height="24"
            class="me-2"
            :src="require('@/assets/images/defi/balancer.svg')"
          />
          {{ $t('liquidity.balancer') }}
        </v-btn>
      </v-btn-toggle>
    </div>
    <router-view />
  </fragment>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Fragment from '@/components/helper/Fragment';
import { Routes } from '@/router/routes';

@Component({
  components: { Fragment }
})
export default class Liquidity extends Vue {
  readonly UNISWAP = Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP;
  readonly BALANCER = Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER;
}
</script>

<style lang="scss" scoped>
.liquidity__navigation {
  margin-top: -26px;
}
</style>
