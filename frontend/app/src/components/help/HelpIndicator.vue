<script setup lang="ts">
const props = defineProps<{ visible: boolean }>();

const emit = defineEmits<{ (e: 'update:visible', visible: boolean): void }>();

const { visible } = toRefs(props);
const { t } = useI18n();

function toggleVisibility() {
  emit('update:visible', !get(visible));
}
</script>

<template>
  <MenuTooltipButton
    :tooltip="t('help_sidebar.tooltip')"
    @click="toggleVisibility()"
  >
    <RuiIcon
      :class="{ [$style.visible]: visible }"
      name="question-line"
    />
  </MenuTooltipButton>
</template>

<style module lang="scss">
.visible {
  transform: rotate(-25deg);
}
</style>
