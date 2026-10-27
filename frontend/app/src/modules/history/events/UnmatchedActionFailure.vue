<script setup lang="ts">
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

/**
 * Why the last action in an unmatched panel failed. It offers no retry: the action's own button,
 * still on the row, is the retry.
 */
const { title, failure } = defineProps<{
  title: string;
  failure: unknown;
}>();

const failureMessage = useFailureMessage();
</script>

<template>
  <FailureStrip
    :retryable="false"
    :title="title"
    :message="failureMessage(failure)"
  />
</template>
