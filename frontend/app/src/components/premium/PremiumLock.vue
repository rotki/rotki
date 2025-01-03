<script setup lang="ts">
import { useLinks } from '@/composables/links';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

defineOptions({
  inheritAttrs: false,
});

defineProps<{
  tooltip?: string;
}>();
const { t } = useI18n();
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
