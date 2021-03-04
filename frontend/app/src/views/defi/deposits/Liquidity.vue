<template>
  <v-container>
    <div
      class="d-flex flex-row align-center justify-center liquidity__navigation"
    >
      <v-btn-toggle v-model="path">
        <v-btn :to="UNISWAP" class="lp-navigation" text :value="UNISWAP">
          <v-img
            contain
            width="24"
            height="24"
            class="me-2"
            :src="require('@/assets/images/defi/uniswap.svg')"
          />
          {{ $t('liquidity.uniswap') }}
        </v-btn>
        <v-btn :to="BALANCER" class="lp-navigation" text :value="BALANCER">
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
    <v-container>
      <keep-alive>
        <router-view />
      </keep-alive>
    </v-container>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Routes } from '@/router/routes';

@Component({
  components: {}
})
export default class Liquidity extends Vue {
  readonly UNISWAP = Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP;
  readonly BALANCER = Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER;

  path = '';

  mounted() {
    this.path = this.$route.path;
  }
}
</script>

<style lang="scss" scoped>
.liquidity {
  &__navigation {
    margin-top: -26px;
  }
}
</style>
