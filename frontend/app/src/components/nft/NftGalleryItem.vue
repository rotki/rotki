<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type StyleValue } from 'vue/types/jsx';
import { type GalleryNft } from '@/types/nfts';

const props = defineProps<{
  item: GalleryNft;
}>();

const { item } = toRefs(props);
const { shouldRenderImage } = useNfts();

const frontendStore = useFrontendSettingsStore();

const { whitelistedDomainsForNftImages } = storeToRefs(frontendStore);
const { updateSetting } = frontendStore;

const imageUrlSource: ComputedRef<string | null> = computed(
  () => get(item).imageUrl
);

const name = computed(() =>
  get(item).name ? get(item).name : get(item).collection.name
);

const renderImage: ComputedRef<boolean> = computed(() => {
  const image = get(imageUrlSource);

  if (!image) {
    return true;
  }

  return shouldRenderImage(image);
});

const imageUrl = computed(() => {
  const image = get(imageUrlSource);

  if (!image || !get(renderImage)) {
    return './assets/images/placeholder.svg';
  }

  return image;
});

const isMediaVideo = computed(() => isVideo(get(imageUrl)));

const { t } = useI18n();
const css = useCssModule();

const domain: ComputedRef<string | null> = computed(() =>
  getDomain(get(imageUrlSource) || '')
);

const { show } = useConfirmStore();

const showAllowDomainConfirmation = () => {
  show(
    {
      title: t(
        'general_settings.nft_setting.update_whitelist_confirmation.title'
      ),
      message: t(
        'general_settings.nft_setting.update_whitelist_confirmation.message',
        {
          domain: get(domain)
        },
        2
      )
    },
    allowDomain
  );
};

const allowDomain = () => {
  const domainVal = get(domain);

  if (!domainVal) {
    return;
  }

  const newWhitelisted = [
    ...get(whitelistedDomainsForNftImages),
    domainVal
  ].filter(uniqueStrings);

  updateSetting({ whitelistedDomainsForNftImages: newWhitelisted });
};

const mediaStyle: ComputedRef<StyleValue> = computed(() => {
  const backgroundColor = get(item).backgroundColor;
  if (!get(renderImage) || !backgroundColor) {
    return {};
  }

  return { backgroundColor };
});
</script>

<template>
  <RuiCard no-padding class="mx-auto overflow-hidden">
    <div class="relative">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :disabled="renderImage"
        :open-delay="400"
        class="w-full"
        tooltip-class="max-w-[10rem]"
      >
        <template #activator>
          <ExternalLink :url="item.externalLink" class="w-full" custom>
            <video
              v-if="isMediaVideo"
              controls
              width="auto"
              :src="imageUrl"
              :style="mediaStyle"
            />
            <AppImage v-else :src="imageUrl" contain :style="mediaStyle" />
          </ExternalLink>
        </template>

        {{ t('nft_balance_table.hidden_hint') }}
      </RuiTooltip>

      <RuiTooltip
        v-if="!renderImage"
        :popper="{ placement: 'top' }"
        :open-delay="400"
        :class="css['unlock-button']"
      >
        <template #activator>
          <RuiButton class="!p-2" icon @click="showAllowDomainConfirmation()">
            <RuiIcon name="lock-unlock-line" size="16" />
          </RuiButton>
        </template>
        {{ t('nft_gallery.allow_domain') }}
        <strong class="text-rui-warning-lighter">{{ domain }}</strong>
      </RuiTooltip>
    </div>
    <div class="flex items-center justify-between gap-2 px-4 mt-2">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        tooltip-class="max-w-[20rem]"
        class="text-truncate block text-subtitle-1 font-medium"
      >
        <template #activator>
          {{ name }}
        </template>
        {{ name }}
      </RuiTooltip>
      <AmountDisplay
        class="text-rui-text-secondary text-subtitle-2"
        :value="item.priceInAsset"
        :asset="item.priceAsset"
      />
    </div>
    <div class="flex items-center justify-between gap-2 px-4">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        tooltip-class="max-w-[20rem]"
        class="text-truncate block text-subtitle-1 font-medium"
      >
        <template #activator>
          {{ item.collection.name }}
        </template>
        {{ item.collection.description }}
      </RuiTooltip>
      <AmountDisplay
        class="text-rui-text-secondary text-subtitle-2"
        :price-asset="item.priceAsset"
        :amount="item.priceInAsset"
        :value="item.priceUsd"
        show-currency="ticker"
        fiat-currency="USD"
      />
    </div>
    <template #footer>
      <div class="grow" />
      <IconLink v-if="item.permalink" :url="item.permalink" text="OpenSea" />
    </template>
  </RuiCard>
</template>

<style lang="scss" module>
video {
  @apply max-w-full h-auto;
}

.unlock-button {
  @apply absolute right-2 bottom-2;
}
</style>
