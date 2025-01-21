<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';

definePage({
  props: true,
});

const props = defineProps<{
  location: NavType | '';
}>();

type NavType = 'uniswap-v2' | 'sushiswap';

interface LiquidityPageInfo {
  id: NavType;
  image: string;
  name: string;
}

const imageSize = '64px';

const pages = {
  'sushiswap': defineAsyncComponent(() => import('@/pages/defi/deposits/liquidity/sushiswap/index.vue')),
  'uniswap-v2': defineAsyncComponent(() => import('@/pages/defi/deposits/liquidity/uniswap-v2/index.vue')),
} as const;

const { t } = useI18n();

const liquidities = computed<LiquidityPageInfo[]>(() => [
  {
    id: 'uniswap-v2',
    image: './assets/images/protocols/uniswap.svg',
    name: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v2'),
  },
  {
    id: 'sushiswap',
    image: './assets/images/protocols/sushiswap.svg',
    name: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.sushiswap'),
  },
]);

const router = useRouter();

const lastLocation = useLocalStorage('rotki.staking.last_liquidity_provider', '');

const location = computed({
  get() {
    return props.location ? props.location : undefined;
  },
  set(value?: NavType) {
    set(lastLocation, value);
  },
});

const [DefineIcon, ReuseIcon] = createReusableTemplate<{ image: string }>();

const page = computed(() => {
  const selectedLocation = get(location);
  return selectedLocation ? pages[selectedLocation] : null;
});

watchImmediate(lastLocation, async (location) => {
  if (!location)
    return;

  await nextTick(() => {
    router.push({
      name: '/defi/deposits/liquidity/[[location]]',
      params: { location },
    });
  });
});
</script>

<template>
  <div class="container">
    <RuiCard class="[&>div:first-child]:flex">
      <DefineIcon #default="{ image }">
        <AdaptiveWrapper
          width="1.5rem"
          height="1.5rem"
        >
          <AppImage
            contain
            width="1.5rem"
            max-height="1.5rem"
            :src="image"
          />
        </AdaptiveWrapper>
      </DefineIcon>
      <RuiMenuSelect
        v-model="location"
        :options="liquidities"
        :label="t('staking_page.dropdown_label')"
        key-attr="id"
        text-attr="name"
        hide-details
        variant="outlined"
      >
        <template #selection="{ item: { image, name } }">
          <div class="flex items-center gap-3">
            <ReuseIcon v-bind="{ image }" />
            {{ name }}
          </div>
        </template>
        <template #item.prepend="{ item: { image } }">
          <ReuseIcon v-bind="{ image }" />
        </template>
      </RuiMenuSelect>
    </RuiCard>

    <div
      v-if="page"
      class="pt-8"
    >
      <Component :is="page" />
    </div>
    <div v-else>
      <div class="flex items-center justify-center md:justify-end mt-2 md:mr-6 text-rui-text-secondary gap-2">
        <RuiIcon
          class="shrink-0"
          name="lu-corner-left-up"
        />
        <div class="pt-3">
          {{ t('staking_page.dropdown_hint') }}
        </div>
      </div>
      <FullSizeContent class="gap-6">
        <span class="font-bold text-h5">
          {{ t('staking_page.page.title') }}
        </span>
        <div class="flex gap-4">
          <RuiTooltip
            v-for="item in liquidities"
            :key="item.id"
            :open-delay="400"
          >
            <template #activator>
              <InternalLink
                :to="{
                  path: '/defi/deposits/liquidity',
                  query: { location },
                }"
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

        <div class="text-body-1 text-rui-text-secondary text-center max-w-[37rem]">
          {{ t('staking_page.page.description') }}
        </div>
      </FullSizeContent>
    </div>
  </div>
</template>
