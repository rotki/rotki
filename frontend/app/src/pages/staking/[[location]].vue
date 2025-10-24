<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { startPromise } from '@shared/utils';
import AppImage from '@/components/common/AppImage.vue';
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import { NoteLocation } from '@/types/notes';
import { getPublicProtocolImagePath } from '@/utils/file';

type NavType = 'eth2' | 'liquity' | 'kraken';

interface StakingInfo {
  id: NavType;
  image: string;
  name: string;
}

definePage({
  meta: {
    noteLocation: NoteLocation.STAKING,
  },
  props: true,
});

const props = defineProps<{
  location: NavType | '';
}>();

const imageSize = '64px';

const pages = {
  eth2: defineAsyncComponent(() => import('@/modules/staking/eth/EthStakingPage.vue')),
  kraken: defineAsyncComponent(() => import('@/components/staking/kraken/KrakenPage.vue')),
  liquity: defineAsyncComponent(() => import('@/components/staking/liquity/LiquityPage.vue')),
};

const { t } = useI18n({ useScope: 'global' });

const lastLocation = useLocalStorage('rotki.staking.last_location', '');

const location = computed({
  get() {
    return props.location || undefined;
  },
  set(value?: NavType) {
    set(lastLocation, value);
    if (value)
      startPromise(redirect(value));
  },
});

const staking = computed<StakingInfo[]>(() => [
  {
    id: 'eth2',
    image: getPublicProtocolImagePath('ethereum.svg'),
    name: t('staking.eth2'),
  },
  {
    id: 'liquity',
    image: getPublicProtocolImagePath('liquity.png'),
    name: t('staking.liquity'),
  },
  {
    id: 'kraken',
    image: getPublicProtocolImagePath('kraken.svg'),
    name: t('staking.kraken'),
  },
]);

const router = useRouter();
const [DefineIcon, ReuseIcon] = createReusableTemplate<{ image: string }>();

function getRedirectLink(location: string): RouteLocationRaw {
  return {
    name: '/staking/[[location]]',
    params: { location },
  };
}

async function redirect(location: string) {
  await nextTick(() => {
    router.push(getRedirectLink(location));
  });
}

const page = computed(() => {
  const selectedLocation = get(location);
  return selectedLocation ? pages[selectedLocation] : null;
});

onMounted(async () => {
  if (props.location) {
    set(location, props.location);
    return;
  }
  const lastLocationVal = get(lastLocation);
  if (!lastLocationVal)
    return;

  await redirect(lastLocationVal);
});
</script>

<template>
  <div class="container">
    <RuiCard class="[&>div:first-child]:flex">
      <DefineIcon #default="{ image }">
        <AppImage
          class="icon-bg"
          contain
          size="1.5rem"
          :src="image"
        />
      </DefineIcon>
      <RuiMenuSelect
        v-model="location"
        :options="staking"
        :label="t('staking_page.dropdown_label')"
        key-attr="id"
        text-attr="name"
        hide-details
        :item-height="52"
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
            v-for="item in staking"
            :key="item.id"
            :open-delay="400"
          >
            <template #activator>
              <InternalLink :to="getRedirectLink(item.id)">
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
