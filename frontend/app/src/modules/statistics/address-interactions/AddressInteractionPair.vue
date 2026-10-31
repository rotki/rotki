<script setup lang="ts">
import type { InteractionNode } from './address-interaction-graph';
import AddressInteractionAddress from './AddressInteractionAddress.vue';
import { PAIR_CHARS } from './use-interaction-labels';

/** One address, or two joined by an arrow and cut shorter so both fit on one line of the side panel. */
const { nodes } = defineProps<{ nodes: readonly InteractionNode[] }>();
</script>

<template>
  <span class="truncate">
    <template
      v-for="(node, index) in nodes"
      :key="node.id"
    >
      <RuiIcon
        v-if="index > 0"
        name="lu-arrow-left-right"
        size="12"
        class="mx-1 inline align-middle text-rui-text-secondary"
        aria-hidden="true"
      />
      <AddressInteractionAddress
        :node="node"
        :chars="nodes.length > 1 ? PAIR_CHARS : undefined"
      />
    </template>
  </span>
</template>
