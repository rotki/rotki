<script setup lang="ts">
import { bridgeMatchingKind } from '@/modules/history/events/matching/bridge-matching-kind';
import UnmatchedMatchingPinned from '@/modules/history/events/UnmatchedMatchingPinned.vue';

defineProps<{
  highlightedGroupIdentifier?: string;
  highlightedPotentialMatchIdentifier?: number;
  potentialMatchGroupIdentifier?: string;
}>();
</script>

<template>
  <UnmatchedMatchingPinned
    v-bind="$props"
    :kind="bridgeMatchingKind"
  />
</template>
