<script setup lang="ts">
const props = defineProps<{ visible: boolean }>();

const emit = defineEmits<{ (e: 'visible:update', visible: boolean): void }>();

const { visible } = toRefs(props);
const { t } = useI18n();

const toggleVisibility = () => {
  emit('visible:update', !get(visible));
};

const css = useCssModule();
</script>

<template>
  <MenuTooltipButton
    :tooltip="t('help_sidebar.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility()"
  >
    <RuiIcon :class="{ [css.visible]: visible }" name="question-line" />
  </MenuTooltipButton>
</template>

<style module lang="scss">
.visible {
  transform: rotate(-25deg);
}
</style>
