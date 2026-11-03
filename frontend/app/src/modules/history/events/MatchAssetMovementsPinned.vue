<script setup lang="ts">
import { assetMovementMatchingKind } from '@/modules/history/events/matching/asset-movement-matching-kind';
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
    :kind="assetMovementMatchingKind"
  />
</template>
