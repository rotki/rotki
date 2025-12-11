<script lang="ts" setup>
import { externalLinks } from '@shared/external-links';
import AppImage from '@/components/common/AppImage.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { useMainStore } from '@/store/main';

const props = defineProps<{
  drawer?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { appVersion } = storeToRefs(useMainStore());

const demoMode = import.meta.env.VITE_DEMO_MODE;

const version = computed<string>(() => {
  const version = get(appVersion);
  if (demoMode === undefined) {
    return version;
  }

  const sanitizedVersion = version.replace('.dev', '');
  const splitVersion = sanitizedVersion.split('.');
  if (demoMode === 'minor') {
    splitVersion[1] = `${parseInt(splitVersion[1]) + 1}`;
    splitVersion[2] = '0';
  }
  else if (demoMode === 'patch') {
    splitVersion[2] = `${parseInt(splitVersion[2]) + 1}`;
  }
  return splitVersion.join('.');
});

interface Sponsor {
  image: string;
  name: string;
}

const sponsors: Sponsor[] = [
  {
    image: '/assets/images/sponsorship/1.42.0_jespow.eth_1.png',
    name: 'jespow.eth',
  },
  {
    image: '/assets/images/sponsorship/1.42.0_jespow.eth_2.png',
    name: 'jespow.eth',
  },
];

const loginIndex = useLocalStorage<number>('rotki.sponsorship.login_index', -1);

function getCurrentSponsor(): Sponsor {
  const length = sponsors.length;
  if (!props.drawer) {
    const loginIndexVal = get(loginIndex);
    // Login screen: determine and save the flipped index
    if (loginIndexVal === -1) {
      set(loginIndex, Math.floor(Math.random() * length));
    }
    else {
      // Flip from previous
      set(loginIndex, (loginIndexVal + 1) % length);
    }
    return sponsors[get(loginIndex)];
  }
  // Drawer: use the opposite of what's stored for login
  const drawerIndex = (get(loginIndex) + 1) % length;
  return sponsors[drawerIndex];
}

const data = ref<Sponsor>(getCurrentSponsor());
</script>

<template>
  <div class="flex flex-wrap gap-1 gap-x-4 w-[400px] max-w-full mx-auto">
    <div class="flex items-center justify-center w-full gap-2">
      <AppImage
        cover
        class="rounded-md overflow-hidden"
        :class="drawer ? 'size-20' : 'size-24 min-w-24'"
        :alt="data.name"
        :src="data.image"
      />
      <div
        class="flex flex-col justify-between flex-1 gap-2"
        :class="{ 'px-4': !drawer }"
      >
        <div class="flex flex-col">
          <div
            class="text-center"
            :class="[
              drawer ? 'text-xs' : 'text-sm',
            ]"
          >
            <div class="font-bold">
              {{ drawer ? version : t('sponsorship.version', { version }) }}
            </div>
            <div class="text-rui-text-secondary">
              {{ t('sponsorship.sponsored_by') }}
            </div>
          </div>
        </div>
        <div
          class="flex flex-col items-center flex-1 w-full font-black text-center rounded-sm px-1.5 py-0.5 relative mb-2"
          :class="[
            drawer ? 'text-sm' : 'leading-6',
          ]"
        >
          <img
            src="/assets/images/ribbon.png"
            class="w-full h-[125%] absolute top-0 left-0 object-fill"
            alt=""
          />

          <div class="relative text-yellow-900 max-w-[80%] px-0.5 text-center">
            {{ data.name }}
          </div>
        </div>
        <div class="w-full flex justify-center">
          <ExternalLink
            color="primary"
            class="!text-xs text-center"
            :url="externalLinks.sponsor"
          >
            {{ t('sponsorship.sponsor') }}
          </ExternalLink>
        </div>
      </div>
    </div>
  </div>
</template>
