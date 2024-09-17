<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

type NavType = 'eth2' | 'liquity' | 'kraken';

interface StakingInfo {
  id: NavType;
  image: string;
  name: string;
}

const props = defineProps<{
  location: NavType | '';
}>();

definePage({
  meta: {
    noteLocation: NoteLocation.STAKING,
  },
  props: true,
});

const imageSize = '64px';

const pages = {
  eth2: defineAsyncComponent(() => import('@/components/staking/eth/EthStakingPage.vue')),
  liquity: defineAsyncComponent(() => import('@/components/staking/liquity/LiquityPage.vue')),
  kraken: defineAsyncComponent(() => import('@/components/staking/kraken/KrakenPage.vue')),
};

const { t } = useI18n();

const lastLocation = useLocalStorage('rotki.staking.last_location', '');

const location = ref<NavType | undefined>(props.location as NavType | undefined);

const staking = computed<StakingInfo[]>(() => [
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

const page = computed(() => {
  const selectedLocation = get(location);
  return selectedLocation ? pages[selectedLocation] : null;
});

function updateLocation(newLocation: NavType | undefined) {
  if (newLocation) {
    set(location, newLocation);
    set(lastLocation, newLocation);
  }
};

watchImmediate(lastLocation, async (location) => {
  if (!location)
    return;

  await nextTick(() => {
    router.push({
      name: '/staking/[[location]]',
      params: { location },
    });
  });
});

watch(() => props.location, (newLocation) => {
  if (newLocation) {
    set(location, newLocation as NavType);
    set(lastLocation, newLocation);
  }
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
        v-model="location"
        :options="staking"
        :label="t('staking_page.dropdown_label')"
        key-attr="id"
        text-attr="name"
        hide-details
        variant="outlined"
        @update:model-value="updateLocation"
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
                  :to="{
                    path: '/staking',
                    query: { location: item.id },
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
        </div>
      </FullSizeContent>
    </div>
  </div>
</template>
