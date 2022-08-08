<template>
  <menu-tooltip-button
    :tooltip="$t('notes_menu.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility"
  >
    <v-icon :class="visible ? 'help--visible' : null"> mdi-note-text </v-icon>
  </menu-tooltip-button>
</template>

<script lang="ts">
import { defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

export default defineComponent({
  name: 'UserNotesIndicator',
  components: { MenuTooltipButton },
  props: {
    visible: { required: true, type: Boolean }
  },
  emits: ['visible:update'],
  setup(props, { emit }) {
    const { visible } = toRefs(props);

    const toggleVisibility = () => {
      emit('visible:update', !get(visible));
    };

    return {
      toggleVisibility
    };
  }
});
</script>

<style scoped lang="scss">
.help {
  &--visible {
    transform: rotate(-25deg);
  }
}
</style>
