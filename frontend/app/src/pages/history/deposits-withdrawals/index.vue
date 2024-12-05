<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.HISTORY_DEPOSITS_WITHDRAWALS,
  },
  name: 'deposits-withdrawals',
});
</script>

<template>
  <DepositsWithdrawalsContent />
</template>
