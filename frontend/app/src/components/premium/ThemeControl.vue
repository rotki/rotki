<script setup lang="ts">
import { ThemeSwitch } from '@/premium/premium';

defineProps({
  darkModeEnabled: {
    required: true,
    type: Boolean
  },
  menu: {
    required: false,
    type: Boolean,
    default: false
  }
});

const { showComponents } = storeToRefs(usePremiumStore());
</script>

<template>
  <div>
    <ThemeSwitch
      v-if="showComponents"
      :dark-mode-enabled="darkModeEnabled"
      :in-menu="menu"
    >
      <slot />
    </ThemeSwitch>
    <ThemeSwitchLock v-else />
  </div>
</template>
