<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import DepositsWithdrawalsContent from '@/components/history/deposits-withdrawals/DepositsWithdrawalsContent.vue';

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
