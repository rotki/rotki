<template>
  <v-card class="mx-auto">
    <v-img
      :src="imageUrl"
      contain
      aspect-ratio="1"
      :style="{
        'background-color': `#${item.backgroundColor}`
      }"
    />
    <v-card-title>
      <v-row align="center" no-gutters>
        <v-col class="text-truncate">
          {{ name }}
        </v-col>
        <v-col cols="auto" class="text-subtitle-2">
          <amount-display
            class="text--secondary"
            :value="item.priceEth"
            asset="ETH"
          />
        </v-col>
      </v-row>
    </v-card-title>
    <v-card-subtitle>
      <v-row align="center" no-gutters>
        <v-col>
          <v-tooltip top open-delay="400" max-width="450">
            <template #activator="{ on, attrs }">
              <span v-bind="attrs" class="text-truncate" v-on="on">
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
    </v-card-subtitle>
    <v-card-actions>
      <v-spacer />
      <icon-link :url="item.permalink" />
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
import IconLink from '@/components/base/IconLink.vue';
import { NftWithAddress } from '@/components/nft/types';

export default defineComponent({
  name: 'NftGalleryItem',
  components: { IconLink },
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
