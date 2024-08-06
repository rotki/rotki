<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  name: 'deposits-withdrawals',
  meta: {
    noteLocation: NoteLocation.HISTORY_DEPOSITS_WITHDRAWALS,
  },
});
</script>

<template>
  <DepositsWithdrawalsContent />
</template>
