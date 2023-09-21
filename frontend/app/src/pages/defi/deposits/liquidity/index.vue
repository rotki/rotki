<script setup lang="ts">
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

<template>
  <div>
    <div
      class="flex flex-row items-center justify-center liquidity__navigation"
    >
      <VBtnToggle v-model="path">
        <VBtn
          v-for="provider in providers"
          :key="provider.route"
          :to="provider.route"
          class="lp-navigation"
          text
          :value="provider.route"
        >
          <AdaptiveWrapper class="me-2">
            <VImg contain width="24" height="24" :src="provider.image" />
          </AdaptiveWrapper>
          {{ provider.text }}
        </VBtn>
      </VBtnToggle>
    </div>
    <div>
      <RouterView />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.liquidity {
  &__navigation {
    margin-top: -26px;
  }
}
</style>
