<script setup lang="ts">
const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{ (e: 'visible:update', visible: boolean): void }>();

const { visible } = toRefs(props);
const { t } = useI18n();

const toggleVisibility = () => {
  emit('visible:update', !get(visible));
};
</script>

<template>
  <MenuTooltipButton
    :tooltip="t('notes_menu.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility()"
  >
    <RuiIcon
      :class="visible ? 'help--visible' : null"
      name="sticky-note-line"
    />
  </MenuTooltipButton>
</template>

<style scoped lang="scss">
.help {
  &--visible {
    transform: rotate(-25deg);
  }
}
</style>
