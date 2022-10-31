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

<script setup lang="ts">
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { useRoute } from '@/composables/router';
import { useAppRoutes } from '@/router/routes';

const { appRoutes } = useAppRoutes();

const providers = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2,
    Routes.DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3,
    Routes.DEFI_DEPOSITS_LIQUIDITY_BALANCER,
    Routes.DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP
  ];
});
const route = useRoute();
const path = ref('');
onMounted(() => {
  set(path, get(route).path);
});
</script>

<style lang="scss" scoped>
.liquidity {
  &__navigation {
    margin-top: -26px;
  }
}
</style>
