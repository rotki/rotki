<template>
  <menu-tooltip-button
    v-if="pinned"
    :tooltip="$t('pinned.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility"
  >
    <v-badge color="primary" dot>
      <v-icon class="pinned" :class="{ 'pinned--visible': visible }">
        mdi-pin
      </v-icon>
    </v-badge>
  </menu-tooltip-button>
</template>

<script lang="ts">
import { get } from '@vueuse/core';
import { defineComponent, toRefs } from 'vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { setupSession } from '@/composables/session';

export default defineComponent({
  name: 'PinnedIndicator',
  components: { MenuTooltipButton },
  props: {
    visible: { required: true, type: Boolean }
  },
  emits: ['visible:update'],
  setup(props, { emit }) {
    const { visible } = toRefs(props);

    const { pinned } = setupSession();

    const toggleVisibility = () => {
      emit('visible:update', !get(visible));
    };

    return {
      pinned,
      toggleVisibility
    };
  }
});
</script>

<style scoped lang="scss">
.pinned {
  transform: rotate(20deg);

  &--visible {
    transform: rotate(45deg);
  }
}
</style>
