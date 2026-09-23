<script setup lang="ts">
import type { BankManifest } from '@/modules/banks/types';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

/**
 * A bank connector with its logo: the logo of the bank it always connects to, or a generic bank
 * icon for a connector like FinTS that reaches many banks.
 */
const { manifest } = defineProps<{ manifest: BankManifest }>();
</script>

<template>
  <div
    class="flex items-center gap-2"
    data-testid="bank-connector-display"
  >
    <LocationIcon
      v-if="manifest.fixedLocation"
      class="shrink-0"
      icon
      :item="manifest.fixedLocation"
    />
    <RuiIcon
      v-else
      class="shrink-0"
      color="secondary"
      name="lu-landmark"
      size="24"
    />
    <span>{{ manifest.displayName }}</span>
  </div>
</template>
