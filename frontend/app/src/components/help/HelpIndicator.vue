<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

const props = defineProps<{ visible: boolean }>();

const emit = defineEmits<{ (e: 'update:visible', visible: boolean): void }>();

const { visible } = toRefs(props);
const { t } = useI18n({ useScope: 'global' });

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
      :class="{ '-rotate-[25deg]': visible }"
      name="lu-circle-question-mark"
    />
  </MenuTooltipButton>
</template>
