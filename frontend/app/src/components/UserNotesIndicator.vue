<template>
  <menu-tooltip-button
    :tooltip="tc('notes_menu.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility"
  >
    <v-icon :class="visible ? 'help--visible' : null"> mdi-note-text </v-icon>
  </menu-tooltip-button>
</template>

<script lang="ts">
import { defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { useI18n } from 'vue-i18n-composable';
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
    const { tc } = useI18n();

    const toggleVisibility = () => {
      emit('visible:update', !get(visible));
    };

    return {
      toggleVisibility,
      tc
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
