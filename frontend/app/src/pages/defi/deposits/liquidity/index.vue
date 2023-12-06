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
      <RuiTabs
        v-model="path"
        required
        color="primary"
        variant="outlined"
        class="border border-default rounded bg-white dark:bg-rui-grey-900 max-w-full"
      >
        <template #default>
          <RuiTab
            v-for="provider in providers"
            :key="provider.route"
            :value="provider.route"
            link
            :to="provider.route"
          >
            <template #prepend>
              <AdaptiveWrapper>
                <VImg contain width="24" height="24" :src="provider.image" />
              </AdaptiveWrapper>
            </template>
            {{ provider.text }}
          </RuiTab>
        </template>
      </RuiTabs>
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
