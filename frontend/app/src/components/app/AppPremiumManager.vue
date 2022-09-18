<template>
  <span />
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { setupPremium } from '@/premium/setup-premium';
import { usePremiumStore } from '@/store/session/premium';
import { useStatusStore } from '@/store/status';

const { premium, componentsLoaded } = storeToRefs(usePremiumStore());
const status = useStatusStore();

watch(premium, async premium => {
  if (!premium) {
    status.resetDefiStatus();
  } else {
    if (get(componentsLoaded)) {
      return;
    }
    await setupPremium(componentsLoaded);
  }
});
</script>
