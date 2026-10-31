<script setup lang="ts">
import type { InteractionNode } from './address-interaction-graph';
import { type AddressLabel, useInteractionLabels } from './use-interaction-labels';

/**
 * An address's short label: its name in the surrounding font, or the bare address in monospace,
 * matching how the rest of the app sets addresses.
 */
const { node, chars } = defineProps<{
  node: InteractionNode;
  /** Characters kept at each end of a bare address; 6 by default. */
  chars?: number;
}>();

const { addressLabelOf } = useInteractionLabels();

const label = computed<AddressLabel>(() => addressLabelOf(node, chars));
</script>

<template>
  <span
    :class="{ 'font-mono': !label.named }"
    data-testid="interaction-address"
    v-text="label.text"
  />
</template>
