<template>
  <v-tooltip bottom z-index="215" class="tooltip-menu-button" open-delay="250">
    <template #activator="{ on: menu }">
      <v-btn
        icon
        :class="className"
        :retain-focus-on-click="retainFocusOnClick"
        @click="click()"
        v-on="{ ...menu, ...onMenu }"
      >
        <slot />
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'MenuTooltipButton',
  props: {
    tooltip: { required: true, type: String, default: '' },
    onMenu: { required: false, type: Object, default: () => {} },
    retainFocusOnClick: { required: false, type: Boolean, default: false },
    className: { required: false, type: String, default: '' }
  },
  emits: ['click'],
  setup(_, { emit }) {
    const click = () => emit('click');

    return {
      click
    };
  }
});
</script>

<style scoped lang="scss">
// v-tooltip will render a span with a height computed to 0
// by v-menu, so we have to force a height here otherwise offset-y
// on the v-menu won't work

.tooltip-menu-button {
  display: block;
}
</style>
