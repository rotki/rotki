<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

const visible = defineModel<boolean>('visible', { required: true });

const { t } = useI18n({ useScope: 'global' });

function toggleVisibility(): void {
  set(visible, !get(visible));
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
