<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  name: 'price-manager',
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.PRICE_MANAGER,
  },
  props: true,
  redirect: '/price-manager/latest',
});
</script>

<template>
  <RouterView />
</template>
