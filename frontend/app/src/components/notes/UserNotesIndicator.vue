<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{ (e: 'update:visible', visible: boolean): void }>();

const { visible } = toRefs(props);
const { t } = useI18n({ useScope: 'global' });

function toggleVisibility() {
  emit('update:visible', !get(visible));
}
</script>

<template>
  <MenuTooltipButton
    :tooltip="t('notes_menu.tooltip')"
    @click="toggleVisibility()"
  >
    <RuiIcon
      :class="visible ? 'help--visible' : null"
      name="lu-notebook"
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
