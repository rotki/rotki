<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.PRICE_MANAGER,
  },
  name: 'price-manager',
  props: true,
  redirect: '/price-manager/latest',
});
</script>

<template>
  <RouterView />
</template>
