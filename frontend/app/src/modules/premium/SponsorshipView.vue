<script lang="ts" setup>
import { externalLinks } from '@shared/external-links';
import { useMainStore } from '@/modules/core/common/use-main-store';
import AppImage from '@/modules/shell/components/AppImage.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { drawer } = defineProps<{
  drawer?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { appVersion: version } = storeToRefs(useMainStore());

interface Sponsor {
  image: string;
  name: string;
}

const data: Sponsor = {
  image: '/assets/images/sponsorship/1.43.0_pcaversaccio.jpg',
  name: 'pcaversaccio',
};
</script>

<template>
  <div class="flex flex-wrap gap-1 gap-x-4 w-[400px] max-w-full mx-auto">
    <div class="flex items-center justify-center w-full gap-2">
      <AppImage
        cover
        class="rounded-md overflow-hidden"
        :class="drawer ? 'size-20 min-w-20' : 'size-24 min-w-24'"
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
            class="!text-xs text-center [&>span]:!whitespace-pre-line"
            :url="externalLinks.sponsor"
          >
            {{ t('sponsorship.sponsor') }}
          </ExternalLink>
        </div>
      </div>
    </div>
  </div>
</template>
