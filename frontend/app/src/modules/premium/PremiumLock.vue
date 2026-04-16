<script setup lang="ts">
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import { useLinks } from '@/modules/shell/layout/use-links';

defineOptions({
  inheritAttrs: false,
});

defineProps<{
  tooltip?: string;
}>();
const { t } = useI18n({ useScope: 'global' });
const { href, onLinkClick } = useLinks();
</script>

<template>
  <MenuTooltipButton
    :tooltip="tooltip ?? t('premium_lock.tooltip')"
    :href="href"
    v-bind="$attrs"
    @click="onLinkClick()"
  >
    <RuiIcon name="lu-lock-keyhole" />
  </MenuTooltipButton>
</template>
