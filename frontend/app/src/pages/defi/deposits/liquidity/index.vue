<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';

const { appRoutes } = useAppRoutes();
const css = useCssModule();

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
    <div :class="css.liquidity__navigation">
      <RuiButtonGroup
        v-model="path"
        required
        color="primary"
        variant="outlined"
      >
        <template #default>
          <RuiButton
            v-for="provider in providers"
            :key="provider.route"
            :to="provider.route"
            :value="provider.route"
          >
            <AdaptiveWrapper class="me-2">
              <VImg contain width="24" height="24" :src="provider.image" />
            </AdaptiveWrapper>
            {{ provider.text }}
          </RuiButton>
        </template>
      </RuiButtonGroup>
    </div>
    <div>
      <RouterView />
    </div>
  </div>
</template>

<style lang="scss" module>
.liquidity {
  &__navigation {
    @apply flex flex-row items-center justify-center -mt-[1.625rem] mb-4;
  }
}
</style>
