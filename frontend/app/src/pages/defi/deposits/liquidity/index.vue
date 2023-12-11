<script setup lang="ts">
import { Routes } from '@/router/routes';

interface LiquidityPageInfo {
  id: string;
  image: string;
  name: string;
}

const props = withDefaults(
  defineProps<{
    location?: 'uniswap_v2' | 'uniswap_v3' | 'balancer' | 'sushiswap' | null;
  }>(),
  {
    location: null
  }
);

const imageSize = '64px';

const pages = {
  uniswap_v2: defineAsyncComponent(
    () => import('@/pages/defi/deposits/liquidity/uniswap_v2/index.vue')
  ),
  uniswap_v3: defineAsyncComponent(
    () => import('@/pages/defi/deposits/liquidity/uniswap_v3/index.vue')
  ),
  balancer: defineAsyncComponent(
    () => import('@/pages/defi/deposits/liquidity/balancer/index.vue')
  ),
  sushiswap: defineAsyncComponent(
    () => import('@/pages/defi/deposits/liquidity/sushiswap/index.vue')
  )
};

const { location } = toRefs(props);

const { t } = useI18n();

const liquidities: ComputedRef<LiquidityPageInfo[]> = computed(() => [
  {
    id: 'uniswap_v2',
    image: './assets/images/protocols/uniswap.svg',
    name: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v2')
  },
  {
    id: 'uniswap_v3',
    image: './assets/images/protocols/uniswap.svg',
    name: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v3')
  },
  {
    id: 'balancer',
    image: './assets/images/protocols/balancer.svg',
    name: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.balancer')
  },
  {
    id: 'sushiswap',
    image: './assets/images/protocols/sushiswap.svg',
    name: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.sushiswap')
  }
]);

const router = useRouter();

const lastLocation = useLocalStorage(
  'rotki.staking.last_liquidity_provider',
  ''
);

const page = computed(() => {
  const selectedLocation = get(location);
  return selectedLocation ? pages[selectedLocation] : null;
});

const updateLocation = async (location: string) => {
  if (location) {
    set(lastLocation, location);
  }
  await router.push(
    Routes.DEFI_DEPOSITS_LIQUIDITY.replace(':location*', location)
  );
};

onBeforeMount(async () => {
  if (get(lastLocation)) {
    await updateLocation(get(lastLocation));
  }
});
</script>

<template>
  <div class="container">
    <RuiCard>
      <VSelect
        :value="location"
        outlined
        hide-details
        :items="liquidities"
        :label="t('staking_page.dropdown_label')"
        item-value="id"
        @change="updateLocation($event)"
      >
        <template v-for="slot in ['item', 'selection']" #[slot]="data">
          <div v-if="data.item" :key="slot" class="flex items-center gap-2">
            <AdaptiveWrapper width="24" height="24">
              <VImg
                width="24px"
                contain
                max-height="24px"
                :src="data.item.image"
              />
            </AdaptiveWrapper>
            {{ data.item.name }}
          </div>
        </template>
      </VSelect>
    </RuiCard>

    <div v-if="page" class="pt-8">
      <Component :is="page" />
    </div>
    <div v-else>
      <div
        class="flex flex-row items-center justify-center justify-md-end mt-2 md:mr-6 text-rui-text-secondary gap-2"
      >
        <RuiIcon class="shrink-0" name="corner-left-up-line" />
        <div class="pt-3">
          {{ t('staking_page.dropdown_hint') }}
        </div>
      </div>
      <FullSizeContent>
        <div class="flex flex-col h-full items-center justify-center gap-6">
          <span class="font-bold text-h5">
            {{ t('staking_page.page.title') }}
          </span>
          <div class="flex gap-4">
            <RuiTooltip
              v-for="item in liquidities"
              :key="item.id"
              open-delay="400"
            >
              <template #activator>
                <InternalLink
                  :to="
                    Routes.DEFI_DEPOSITS_LIQUIDITY.replace(
                      ':location*',
                      item.id
                    )
                  "
                >
                  <AppImage
                    :size="imageSize"
                    contain
                    :src="item.image"
                  />
                </InternalLink>
              </template>
              {{ item.name }}
            </RuiTooltip>
          </div>

          <div
            class="text-body-1 text-rui-text-secondary text-center max-w-[37rem]"
          >
            {{ t('staking_page.page.description') }}
          </div>
        </div>
      </FullSizeContent>
    </div>
  </div>
</template>
