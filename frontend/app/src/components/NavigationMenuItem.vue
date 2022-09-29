<template>
  <div class="d-flex flex-grow-1">
    <v-tooltip v-if="showTooltips" right>
      <template #activator="{ on }">
        <v-list-item-icon class="my-3 mr-4" v-on="on">
          <v-img
            v-if="image"
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
    <v-list-item-icon v-else class="my-3 mr-4">
      <v-img
        v-if="image"
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

<script setup lang="ts">
import { PropType, VueConstructor } from 'vue';
import { useTheme } from '@/composables/common';

defineProps({
  showTooltips: { required: false, type: Boolean, default: false },
  icon: { required: false, type: String, default: '' },
  text: { required: true, type: String },
  image: { required: false, type: String, default: '' },
  iconComponent: {
    required: false,
    type: Object as PropType<VueConstructor>,
    default: null
  },
  active: { required: false, type: Boolean, default: false }
});

const { dark } = useTheme();
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
