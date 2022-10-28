<template>
  <span />
</template>

<script setup lang="ts">
import { loadLibrary } from '@/premium/premium';
import { setupPremium } from '@/premium/setup-premium';
import { usePremiumStore } from '@/store/session/premium';
import { useStatusStore } from '@/store/status';

const { premium, componentsReady } = storeToRefs(usePremiumStore());
const status = useStatusStore();

async function setupComponents(): Promise<void> {
  await setupPremium();
  try {
    await loadLibrary();
  } finally {
    set(componentsReady, true);
  }
}

onMounted(async () => {
  set(componentsReady, false);
  if (get(premium)) {
    await setupComponents();
  }
});

watch(premium, async premium => {
  set(componentsReady, false);
  if (!premium) {
    status.resetDefiStatus();
  } else {
    await setupComponents();
  }
});
</script>
