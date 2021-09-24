<template>
  <v-card class="mx-auto">
    <base-external-link :href="item.externalLink">
      <v-img
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
            class="text-truncate text-subtitle-1 font-weight-medium"
            cols="8"
            sm="6"
            lg="7"
            xl="8"
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
              :value="item.priceEth"
              asset="ETH"
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
          <v-col cols="8" sm="6" lg="7" xl="8" class="text-truncate">
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
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import IconLink from '@/components/base/IconLink.vue';
import { NftWithAddress } from '@/components/nft/types';

export default defineComponent({
  name: 'NftGalleryItem',
  components: { BaseExternalLink, IconLink },
  props: {
    item: {
      required: true,
      type: Object as PropType<NftWithAddress>
    }
  },
  setup(props) {
    const { item } = toRefs(props);
    const name = computed(() =>
      item.value.name ? item.value.name : item.value.collection.name
    );
    const imageUrl = computed(() => {
      return item.value.imageUrl ?? require('@/assets/images/placeholder.svg');
    });
    return { name, imageUrl };
  }
});
</script>

<style lang="scss" module>
.title {
  width: 100%;
}
</style>
