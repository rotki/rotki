<script setup lang="ts">
const { t } = useI18n();
const { href, onLinkClick } = useLinks();
</script>

<template>
  <MenuTooltipButton
    :tooltip="t('premium_lock.tooltip')"
    class-name="secondary--text text--lighten-4"
    :href="href"
    @click="onLinkClick()"
  >
    <RuiIcon name="lock-line" />
  </MenuTooltipButton>
</template>
