<script setup lang="ts">
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
    <RuiIcon name="lock-line" />
  </MenuTooltipButton>
</template>
