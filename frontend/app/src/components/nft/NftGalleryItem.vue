<template>
  <v-card class="mx-auto overflow-hidden">
    <base-external-link :href="item.externalLink">
      <video
        v-if="isVideo"
        controls
        width="auto"
        :src="imageUrl"
        :style="{
          'background-color': `#${item.backgroundColor}`
        }"
      />
      <v-img
        v-else
        :src="imageUrl"
        contain
        aspect-ratio="1"
        :style="{
          'background-color': `#${item.backgroundColor}`
        }"
      />
    </base-external-link>
    <v-card-title>
      <div :class="$style.title">
        <v-row align="center" justify="space-between" class="flex-nowrap">
          <v-col
            class="text-truncate text-subtitle-1 font-weight-medium shrink"
            cols="auto"
          >
            <v-tooltip top open-delay="400" max-width="450">
              <template #activator="{ on, attrs }">
                <span v-bind="attrs" v-on="on">
                  {{ name }}
                </span>
              </template>
              <span> {{ name }}</span>
            </v-tooltip>
          </v-col>
          <v-col cols="auto" class="text-subtitle-2">
            <amount-display
              class="text--secondary"
              :value="item.priceInAsset"
              :asset="item.priceAsset"
            />
          </v-col>
        </v-row>
      </div>
    </v-card-title>
    <v-card-subtitle>
      <div :class="$style.title">
        <v-row
          align="center"
          no-gutters
          justify="space-between"
          class="flex-nowrap"
        >
          <v-col cols="auto" class="text-truncate shrink pr-1">
            <v-tooltip top open-delay="400" max-width="450">
              <template #activator="{ on, attrs }">
                <span v-bind="attrs" v-on="on">
                  {{ item.collection.name }}
                </span>
              </template>
              <span> {{ item.collection.description }}</span>
            </v-tooltip>
          </v-col>
          <v-col cols="auto" class="text-subtitle-2">
            <amount-display
              class="text--secondary"
              :value="item.priceUsd"
              show-currency="ticker"
              fiat-currency="USD"
            />
          </v-col>
        </v-row>
      </div>
    </v-card-subtitle>
    <v-card-actions>
      <v-spacer />
      <icon-link :url="item.permalink" text="OpenSea" />
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import IconLink from '@/components/base/IconLink.vue';
import { GalleryNft } from '@/store/session/types';
import { isVideo } from '@/utils/nft';

export default defineComponent({
  name: 'NftGalleryItem',
  components: { BaseExternalLink, IconLink },
  props: {
    item: {
      required: true,
      type: Object as PropType<GalleryNft>
    }
  },
  setup(props) {
    const { item } = toRefs(props);
    const name = computed(() =>
      get(item).name ? get(item).name : get(item).collection.name
    );

    const imageUrl = computed(() => {
      return get(item).imageUrl ?? '/assets/images/placeholder.svg';
    });

    const isMediaVideo = computed(() => {
      return isVideo(get(item).imageUrl);
    });

    return { name, imageUrl, isVideo: isMediaVideo };
  }
});
</script>

<style lang="scss" module>
video {
  max-width: 100%;
  height: auto;
}

.title {
  width: 100%;
}
</style>
