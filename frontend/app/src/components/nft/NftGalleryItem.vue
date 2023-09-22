<script setup lang="ts">
import { type ComputedRef, type PropType } from 'vue';
import { type StyleValue } from 'vue/types/jsx';
import { type GalleryNft } from '@/types/nfts';

const props = defineProps({
  item: {
    required: true,
    type: Object as PropType<GalleryNft>
  }
});

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
  <VCard class="mx-auto overflow-hidden">
    <div :class="css.wrapper">
      <VTooltip top :disabled="renderImage" max-width="200" open-delay="200">
        <template #activator="{ on }">
          <div v-on="on">
            <BaseExternalLink :href="item.externalLink">
              <video
                v-if="isMediaVideo"
                controls
                width="auto"
                :src="imageUrl"
                :style="mediaStyle"
              />
              <VImg
                v-else
                :src="imageUrl"
                contain
                aspect-ratio="1"
                :style="mediaStyle"
              />
            </BaseExternalLink>
          </div>
        </template>

        <span>
          {{ t('nft_balance_table.hidden_hint') }}
        </span>
      </VTooltip>

      <VTooltip v-if="!renderImage" top max-width="200">
        <template #activator="{ on }">
          <RuiButton
            icon
            variant="text"
            :class="css['unlock-button']"
            @click="showAllowDomainConfirmation()"
            v-on="on"
          >
            <VIcon>mdi-camera-lock-open</VIcon>
          </RuiButton>
        </template>
        <span>
          {{ t('nft_gallery.allow_domain') }}
          <span class="font-bold warning--text">{{ domain }}</span>
        </span>
      </VTooltip>
    </div>
    <VCardTitle>
      <div :class="css.title">
        <VRow align="center" justify="space-between" class="flex-nowrap">
          <VCol
            class="text-truncate text-subtitle-1 font-medium shrink"
            cols="auto"
          >
            <VTooltip top open-delay="400" max-width="450">
              <template #activator="{ on, attrs }">
                <span v-bind="attrs" v-on="on">
                  {{ name }}
                </span>
              </template>
              <span> {{ name }}</span>
            </VTooltip>
          </VCol>
          <VCol cols="auto" class="text-subtitle-2">
            <AmountDisplay
              class="text--secondary"
              :value="item.priceInAsset"
              :asset="item.priceAsset"
            />
          </VCol>
        </VRow>
      </div>
    </VCardTitle>
    <VCardSubtitle>
      <div :class="$style.title">
        <VRow
          align="center"
          no-gutters
          justify="space-between"
          class="flex-nowrap"
        >
          <VCol cols="auto" class="text-truncate shrink pr-1">
            <VTooltip top open-delay="400" max-width="450">
              <template #activator="{ on, attrs }">
                <span v-bind="attrs" v-on="on">
                  {{ item.collection.name }}
                </span>
              </template>
              <span> {{ item.collection.description }}</span>
            </VTooltip>
          </VCol>
          <VCol cols="auto" class="text-subtitle-2">
            <AmountDisplay
              class="text--secondary"
              :price-asset="item.priceAsset"
              :amount="item.priceInAsset"
              :value="item.priceUsd"
              show-currency="ticker"
              fiat-currency="USD"
            />
          </VCol>
        </VRow>
      </div>
    </VCardSubtitle>
    <VCardActions>
      <VSpacer />
      <IconLink v-if="item.permalink" :url="item.permalink" text="OpenSea" />
    </VCardActions>
  </VCard>
</template>

<style lang="scss" module>
video {
  max-width: 100%;
  height: auto;
}

.title {
  width: 100%;
}

.wrapper {
  position: relative;
}

.unlock-button {
  position: absolute;
  right: 0.5rem;
  bottom: 0.5rem;
  background-color: var(--border-color) !important;
}
</style>
