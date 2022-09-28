<template>
  <menu-tooltip-button
    :tooltip="tc('notes_menu.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility"
  >
    <v-icon :class="visible ? 'help--visible' : null"> mdi-note-text </v-icon>
  </menu-tooltip-button>
</template>

<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

const props = defineProps({
  visible: { required: true, type: Boolean }
});

const emit = defineEmits<{ (e: 'visible:update', visible: boolean): void }>();

const { visible } = toRefs(props);
const { tc } = useI18n();

const toggleVisibility = () => {
  emit('visible:update', !get(visible));
};
</script>

<style scoped lang="scss">
.help {
  &--visible {
    transform: rotate(-25deg);
  }
}
</style>
