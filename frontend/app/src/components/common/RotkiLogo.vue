<script setup lang="ts">
import type { LogoProps } from '@rotki/ui-library';

withDefaults(
  defineProps<{
    logo?: LogoProps['logo'];
    uniqueKey?: LogoProps['uniqueKey'];
    text?: LogoProps['text'];
    size?: LogoProps['size'];
  }>(),
  {
    logo: 'app',
    uniqueKey: undefined,
    size: undefined,
    text: false,
  },
);

const attrs = useAttrs();
const branch = checkIfDevelopment() ? 'develop' : 'main';
</script>

<template>
  <RuiLogo
    v-bind="attrs"
    :branch="branch"
    :logo="logo"
    :text="text"
    :size="size"
    :unique-key="uniqueKey"
  />
</template>
