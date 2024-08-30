<script setup lang="ts">
const props = defineProps<{ visible: boolean }>();

const emit = defineEmits<{ (e: 'update:visible', visible: boolean): void }>();

const { visible } = toRefs(props);
const { pinned } = storeToRefs(useAreaVisibilityStore());
const { t } = useI18n();

function toggleVisibility() {
  emit('update:visible', !get(visible));
}
</script>

<template>
  <MenuTooltipButton
    v-if="pinned"
    :tooltip="t('pinned.tooltip')"
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
      <RuiIcon
        :class="{ [$style.visible]: visible }"
        name="pushpin-line"
      />
    </RuiBadge>
  </MenuTooltipButton>
</template>

<style module lang="scss">
.visible {
  transform: rotate(-25deg);
}
</style>
