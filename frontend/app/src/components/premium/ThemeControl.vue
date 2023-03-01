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
    <theme-switch
      v-if="showComponents"
      :dark-mode-enabled="darkModeEnabled"
      :in-menu="menu"
    >
      <slot />
    </theme-switch>
    <theme-switch-lock v-else />
  </div>
</template>
