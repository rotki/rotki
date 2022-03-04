<template>
  <div class="d-flex flex-grow-1">
    <v-tooltip v-if="showTooltips" right>
      <template #activator="{ on }">
        <v-list-item-icon class="mr-6" v-on="on">
          <asset-icon
            v-if="!!cryptoIcon"
            :identifier="identifier"
            size="24px"
          />
          <v-img
            v-else-if="image"
            contain
            width="24px"
            :src="image"
            class="nav-icon"
            :class="{
              [$style.image]: true,
              [$style['image--inverted']]: dark
            }"
          />
          <component
            :is="iconComponent"
            v-else-if="iconComponent"
            :active="active"
          />
          <v-icon v-else>{{ icon }}</v-icon>
        </v-list-item-icon>
      </template>
      <span>{{ text }}</span>
    </v-tooltip>
    <v-list-item-icon v-else class="mr-6">
      <asset-icon v-if="!!cryptoIcon" :identifier="identifier" size="24px" />
      <v-img
        v-else-if="image"
        contain
        width="24px"
        :src="image"
        class="nav-icon"
        :class="{
          [$style.image]: true,
          [$style['image--inverted']]: dark
        }"
      />
      <component
        :is="iconComponent"
        v-else-if="iconComponent"
        :active="active"
      />
      <v-icon v-else>{{ icon }}</v-icon>
    </v-list-item-icon>
    <v-list-item-content class="d-flex flex-grow-1">
      <v-list-item-title>{{ text }}</v-list-item-title>
    </v-list-item-content>
  </div>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { VueConstructor } from 'vue';
import { setupThemeCheck } from '@/composables/common';
import { useAssetInfoRetrieval } from '@/store/assets';

export default defineComponent({
  name: 'NavigationMenuItem',
  props: {
    showTooltips: { required: false, type: Boolean, default: false },
    icon: { required: false, type: String, default: '' },
    cryptoIcon: { required: false, type: String, default: '' },
    text: { required: true, type: String },
    image: { required: false, type: String, default: '' },
    iconComponent: {
      required: false,
      type: Object as PropType<VueConstructor>,
      default: null
    },
    active: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { cryptoIcon } = toRefs(props);
    const { assetIdentifierForSymbol } = useAssetInfoRetrieval();

    const identifier = computed<string>(() => {
      return get(assetIdentifierForSymbol(get(cryptoIcon))) ?? get(cryptoIcon);
    });

    const { dark } = setupThemeCheck();

    return {
      dark,
      identifier
    };
  }
});
</script>

<style module lang="scss">
.image {
  opacity: 0.7;
  filter: brightness(0);

  &--inverted {
    opacity: 1;
    filter: brightness(0) invert(100%);
  }
}
</style>
