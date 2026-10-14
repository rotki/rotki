<script setup lang="ts">
import { toSentenceCase } from '@rotki/common';

/** How a rule processes its event, as a one-line chip; a rule with no treatment shows a dash. */
defineProps<{
  treatment?: string | null;
}>();
</script>

<template>
  <RuiChip
    v-if="treatment"
    size="sm"
    color="grey"
    class="whitespace-nowrap"
  >
    {{ toSentenceCase(treatment) }}
  </RuiChip>
  <span
    v-else
    class="text-rui-text-secondary"
  >
    -
  </span>
</template>
