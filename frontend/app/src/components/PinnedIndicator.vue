<script setup lang="ts">
const props = defineProps<{ visible: boolean }>();

const emit = defineEmits<{ (e: 'visible:update', visible: boolean): void }>();

const { visible } = toRefs(props);
const { pinned } = storeToRefs(useAreaVisibilityStore());
const { t } = useI18n();

const toggleVisibility = () => {
  emit('visible:update', !get(visible));
};

const css = useCssModule();
</script>

<template>
  <MenuTooltipButton
    v-if="pinned"
    :tooltip="t('pinned.tooltip')"
    class-name="secondary--text text--lighten-4"
    @click="toggleVisibility()"
  >
    <RuiBadge
      color="primary"
      dot
      placement="top"
      offset-y="4"
      size="lg"
      class="flex items-center"
    >
      <RuiIcon :class="{ [css.visible]: visible }" name="pushpin-line" />
    </RuiBadge>
  </MenuTooltipButton>
</template>

<style module lang="scss">
.visible {
  transform: rotate(-25deg);
}
</style>
