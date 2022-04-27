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
          <adaptive-wrapper class="me-2">
            <v-img contain width="24" height="24" :src="provider.image" />
          </adaptive-wrapper>
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
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { Routes } from '@/router/routes';

const providers = [
  Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP,
  Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER,
  Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP
];
export default defineComponent({
  name: 'Liquidity',
  components: { AdaptiveWrapper },
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
