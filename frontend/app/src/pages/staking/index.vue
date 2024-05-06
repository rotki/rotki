<script setup lang="ts">
import { Routes } from '@/router/routes';

interface StakingInfo {
  id: string;
  image: string;
  name: string;
}

const props = withDefaults(
  defineProps<{
    location?: 'eth2' | 'liquity' | 'kraken' | null;
  }>(),
  {
    location: null,
  },
);

const imageSize = '64px';

const pages = {
  eth2: defineAsyncComponent(
    () => import('@/components/staking/eth/EthStakingPage.vue'),
  ),
  liquity: defineAsyncComponent(
    () => import('@/components/staking/liquity/LiquityPage.vue'),
  ),
  kraken: defineAsyncComponent(
    () => import('@/components/staking/kraken/KrakenPage.vue'),
  ),
};

const { location } = toRefs(props);

const { t } = useI18n();

const staking: ComputedRef<StakingInfo[]> = computed(() => [
  {
    id: 'eth2',
    image: './assets/images/protocols/ethereum.svg',
    name: t('staking.eth2'),
  },
  {
    id: 'liquity',
    image: './assets/images/protocols/liquity.png',
    name: t('staking.liquity'),
  },
  {
    id: 'kraken',
    image: './assets/images/protocols/kraken.svg',
    name: t('staking.kraken'),
  },
]);

const router = useRouter();
const [DefineIcon, ReuseIcon] = createReusableTemplate<{ image: string }>();

const lastLocation = useLocalStorage('rotki.staking.last_location', '');

const page = computed(() => {
  const selectedLocation = get(location);
  return selectedLocation ? pages[selectedLocation] : null;
});

async function updateLocation(location: string) {
  if (location)
    set(lastLocation, location);

  await router.push(Routes.STAKING.replace(':location*', location));
}

onBeforeMount(async () => {
  if (get(lastLocation))
    await updateLocation(get(lastLocation));
});
</script>

<template>
  <div class="container">
    <RuiCard>
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
        :value="location"
        :options="staking"
        :label="t('staking_page.dropdown_label')"
        key-attr="id"
        text-attr="name"
        full-width
        variant="outlined"
        @input="updateLocation($event)"
      >
        <template #activator.text="{ value: { image, name } }">
          <div class="flex items-center gap-3">
            <ReuseIcon v-bind="{ image }" />
            {{ name }}
          </div>
        </template>
        <template #item.prepend="{ option: { image } }">
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
      <div
        class="flex items-center justify-center md:justify-end mt-2 md:mr-6 text-rui-text-secondary gap-2"
      >
        <RuiIcon
          class="shrink-0"
          name="corner-left-up-line"
        />
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
              v-for="item in staking"
              :key="item.id"
              :open-delay="400"
            >
              <template #activator>
                <InternalLink
                  :to="Routes.STAKING.replace(':location*', item.id)"
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
