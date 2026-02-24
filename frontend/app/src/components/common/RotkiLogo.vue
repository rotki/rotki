<script setup lang="ts">
import type { LogoProps } from '@rotki/ui-library';
import { checkIfDevelopment } from '@shared/utils';

defineOptions({
  inheritAttrs: false,
});

const { text = false, uniqueKey, size } = defineProps<{
  uniqueKey?: LogoProps['uniqueKey'];
  text?: LogoProps['text'];
  size?: LogoProps['size'];
}>();

const branch = checkIfDevelopment() ? 'develop' : 'main';
</script>

<template>
  <RuiLogo
    v-bind="$attrs"
    logo="app"
    :branch="branch"
    :text="text"
    :size="size"
    :unique-key="uniqueKey"
  />
</template>
