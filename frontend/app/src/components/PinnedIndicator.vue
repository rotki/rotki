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

<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const props = defineProps({
  visible: { required: true, type: Boolean }
});

const emit = defineEmits<{ (e: 'visible:update', visible: boolean): void }>();

const { visible } = toRefs(props);
const { pinned } = storeToRefs(useAreaVisibilityStore());
const { tc } = useI18n();

const toggleVisibility = () => {
  emit('visible:update', !get(visible));
};
</script>

<style scoped lang="scss">
.pinned {
  transform: rotate(20deg);

  &--visible {
    transform: rotate(45deg);
  }
}
</style>
