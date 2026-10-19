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
  image: '/assets/images/sponsorship/1.44.0_ambire.png',
  name: 'Ambire Wallet',
};
</script>

<template>
  <div class="flex flex-wrap gap-1 gap-x-4 w-100 max-w-full mx-auto">
    <div class="flex items-center justify-center w-full gap-2">
      <AppImage
        fit="cover"
        class="rounded-md overflow-hidden"
        :class="drawer ? 'size-16 min-w-16' : 'size-24 min-w-24'"
        :alt="data.name"
        :src="data.image"
      />
      <div
        class="flex flex-col justify-between flex-1"
        :class="drawer ? 'gap-2' : 'gap-2 px-4'"
      >
        <div class="flex flex-col">
          <div
            class="text-center"
            :class="[
              drawer ? 'text-xs' : 'text-sm',
            ]"
          >
            <div
              v-if="!drawer"
              class="font-medium"
            >
              {{ t('sponsorship.version', { version }) }}
            </div>
            <div class="text-rui-text-secondary">
              {{ t('sponsorship.sponsored_by') }}
            </div>
          </div>
        </div>
        <div
          class="flex flex-col items-center flex-1 w-full font-bold text-center rounded-xs px-1.5 pt-0.5 pb-2.5 relative"
          :class="[
            drawer ? 'text-sm' : 'leading-6',
          ]"
        >
          <img
            src="/assets/images/ribbon.png"
            class="w-full h-full absolute top-0 left-0 object-fill"
            alt=""
          />

          <div
            class="relative text-yellow-900 max-w-[70%] px-0.5 text-center truncate"
            :title="data.name"
          >
            {{ data.name }}
          </div>
        </div>
        <div class="w-full flex justify-center">
          <ExternalLink
            color="primary"
            class="text-xs text-center whitespace-pre-line"
            :url="externalLinks.sponsor"
          >
            {{ t('sponsorship.sponsor') }}
          </ExternalLink>
        </div>
        <div
          v-if="drawer"
          class="pt-1.5 text-center text-xs text-rui-text-disabled tabular-nums"
          data-testid="sponsorship-version"
        >
          {{ t('sponsorship.version', { version }) }}
        </div>
      </div>
    </div>
  </div>
</template>
