<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useLinks } from '@/composables/links';

const { href, onLinkClick } = useLinks();
const { t } = useI18n();
</script>

<template>
  <RuiBadge
    placement="top"
    offset-y="12"
    offset-x="-10"
    size="sm"
  >
    <template #icon>
      <RuiIcon
        name="lu-lock-keyhole"
        size="10"
      />
    </template>
    <MenuTooltipButton
      :tooltip="t('theme_switch_lock.tooltip')"
      :href="href"
      @click="onLinkClick()"
    >
      <RuiIcon name="lu-sun" />
    </MenuTooltipButton>
  </RuiBadge>
</template>
