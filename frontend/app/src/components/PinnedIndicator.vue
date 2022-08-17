<template>
  <menu-tooltip-button
    v-if="pinned"
    :tooltip="tc('pinned.tooltip')"
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
import { defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useAreaVisibilityStore } from '@/store/session/visibility';

export default defineComponent({
  name: 'PinnedIndicator',
  components: { MenuTooltipButton },
  props: {
    visible: { required: true, type: Boolean }
  },
  emits: ['visible:update'],
  setup(props, { emit }) {
    const { visible } = toRefs(props);

    const { pinned } = storeToRefs(useAreaVisibilityStore());
    const { tc } = useI18n();

    const toggleVisibility = () => {
      emit('visible:update', !get(visible));
    };

    return {
      pinned,
      toggleVisibility,
      tc
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
