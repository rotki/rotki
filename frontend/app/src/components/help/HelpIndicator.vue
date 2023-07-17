<script setup lang="ts">
const props = defineProps({
  visible: { required: true, type: Boolean }
});

const emit = defineEmits<{ (e: 'visible:update', visible: boolean): void }>();

const { visible } = toRefs(props);
const { t } = useI18n();

const toggleVisibility = () => {
  emit('visible:update', !get(visible));
};
</script>

<template>
  <MenuTooltipButton
    :tooltip="t('help_sidebar.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility()"
  >
    <VIcon :class="visible ? 'help--visible' : null"> mdi-help-circle </VIcon>
  </MenuTooltipButton>
</template>

<style scoped lang="scss">
.help {
  &--visible {
    transform: rotate(-25deg);
  }
}
</style>
