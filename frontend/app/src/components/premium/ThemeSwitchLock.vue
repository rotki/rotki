<script setup lang="ts">
const { href, onLinkClick } = useLinks();
const { t } = useI18n();
</script>

<template>
  <RuiBadge
    placement="top"
    offset-y="12"
    offset-x="-10"
    size="sm"
    color="default"
  >
    <template #icon>
      <RuiIcon
        name="lock-line"
        color="primary"
        size="14"
      />
    </template>
    <MenuTooltipButton
      :tooltip="t('theme_switch_lock.tooltip')"
      :href="href"
      @click="onLinkClick()"
    >
      <RuiIcon name="sun-line" />
    </MenuTooltipButton>
  </RuiBadge>
</template>
