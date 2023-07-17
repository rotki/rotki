<script setup lang="ts">
import { type PropType, type VueConstructor } from 'vue';

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
  active: { required: false, type: Boolean, default: false },
  subMenu: { required: false, type: Boolean, default: false }
});

const { dark } = useTheme();

const css = useCssModule();
</script>

<template>
  <div class="d-flex flex-grow-1">
    <VTooltip v-if="showTooltips" right>
      <template #activator="{ on }">
        <VListItemIcon :class="subMenu ? 'my-2 mr-2' : 'my-3 mr-3'" v-on="on">
          <VImg
            v-if="image"
            contain
            width="24px"
            :src="image"
            class="nav-icon"
            :class="{
              [css.image]: true,
              [css['image--inverted']]: dark
            }"
          />
          <Component
            :is="iconComponent"
            v-else-if="iconComponent"
            :active="active"
          />
          <VIcon v-else>{{ icon }}</VIcon>
        </VListItemIcon>
      </template>
      <span>{{ text }}</span>
    </VTooltip>
    <VListItemIcon v-else :class="subMenu ? 'my-2 mr-2' : 'my-3 mr-3'">
      <VImg
        v-if="image"
        contain
        width="24px"
        :src="image"
        class="nav-icon"
        :class="{
          [css.image]: true,
          [css['image--inverted']]: dark
        }"
      />
      <Component
        :is="iconComponent"
        v-else-if="iconComponent"
        :active="active"
      />
      <VIcon v-else>{{ icon }}</VIcon>
    </VListItemIcon>
    <VListItemContent class="d-flex flex-grow-1 py-0">
      <VListItemTitle :class="{ [css.small]: subMenu }">
        {{ text }}
      </VListItemTitle>
    </VListItemContent>
  </div>
</template>

<style module lang="scss">
.image {
  opacity: 0.7;
  filter: brightness(0);

  &--inverted {
    opacity: 1;
    filter: brightness(0) invert(100%);
  }
}

.small {
  font-size: 0.875rem;
}
</style>
