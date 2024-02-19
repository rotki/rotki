<script setup lang="ts">
import { ThemeSwitch } from '@/premium/premium';

withDefaults(
  defineProps<{
    darkModeEnabled: boolean;
    menu?: boolean;
  }>(),
  {
    menu: false,
  },
);

const premium = usePremium();
</script>

<template>
  <div>
    <ThemeSwitch
      v-if="premium"
      :dark-mode-enabled="darkModeEnabled"
      :in-menu="menu"
    >
      <slot />
    </ThemeSwitch>
    <ThemeSwitchLock v-else />
  </div>
</template>
