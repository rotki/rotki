<template>
  <div>
    <div
      class="d-flex flex-row align-center justify-center liquidity__navigation"
    >
      <v-btn-toggle v-model="path">
        <v-btn
          v-for="provider in providers"
          :key="provider.route"
          :to="provider.route"
          class="lp-navigation"
          text
          :value="provider.route"
        >
          <v-img
            contain
            width="24"
            height="24"
            class="me-2"
            :src="provider.icon"
          />
          {{ provider.text }}
        </v-btn>
      </v-btn-toggle>
    </div>
    <div>
      <keep-alive>
        <router-view />
      </keep-alive>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from '@vue/composition-api';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';

const providers = [
  {
    route: Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP,
    icon: require('@/assets/images/defi/uniswap.svg'),
    text: i18n.t('liquidity.uniswap').toString()
  },
  {
    route: Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER,
    icon: require('@/assets/images/defi/balancer.svg'),
    text: i18n.t('liquidity.balancer').toString()
  },
  {
    route: Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP,
    icon: require('@/assets/images/modules/sushiswap.svg'),
    text: i18n.t('liquidity.sushiswap').toString()
  }
];
export default defineComponent({
  name: 'Liquidity',
  setup() {
    const path = ref('');
    return {
      providers,
      path
    };
  },
  mounted() {
    this.path = this.$route.path;
  }
});
</script>

<style lang="scss" scoped>
.liquidity {
  &__navigation {
    margin-top: -26px;
  }
}
</style>
