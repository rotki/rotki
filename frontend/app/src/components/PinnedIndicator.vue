<script setup lang="ts">
const props = defineProps({
  visible: { required: true, type: Boolean }
});

const emit = defineEmits<{ (e: 'visible:update', visible: boolean): void }>();

const { visible } = toRefs(props);
const { pinned } = storeToRefs(useAreaVisibilityStore());
const { t } = useI18n();

const toggleVisibility = () => {
  emit('visible:update', !get(visible));
};
</script>

<template>
  <MenuTooltipButton
    v-if="pinned"
    :tooltip="t('pinned.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility()"
  >
    <VBadge color="primary" dot>
      <VIcon class="pinned" :class="{ 'pinned--visible': visible }">
        mdi-pin
      </VIcon>
    </VBadge>
  </MenuTooltipButton>
</template>

<style scoped lang="scss">
.pinned {
  transform: rotate(20deg);

  &--visible {
    transform: rotate(45deg);
  }
}
</style>
