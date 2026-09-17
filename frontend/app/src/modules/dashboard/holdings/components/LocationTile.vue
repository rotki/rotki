<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { LocationHolding } from '@/modules/dashboard/holdings/core/holdings-types';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { SOURCE_KIND_COLOR } from '@/modules/dashboard/holdings/source-kind-style';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';

const { holding, showKinds = true } = defineProps<{
  holding: LocationHolding;
  label: string;
  to: RouteLocationRaw;
  /** Share of the strip's total, as a percentage string. */
  share: string;
  /** Marks for the kinds held here; pointless once the strip is narrowed to one kind. */
  showKinds?: boolean;
}>();

defineSlots<{
  badge?: () => any;
}>();

const kindMarks = computed<boolean>(() => showKinds && holding.parts.length > 1);
</script>

<template>
  <RouterLink
    :to="to"
    class="grid grid-cols-[28px_1fr] items-center gap-x-2.5 min-w-0 !text-rui-text rounded-md border border-transparent bg-rui-grey-100 dark:bg-rui-grey-900 px-3 py-2 hover:border-default hover:bg-white dark:hover:bg-rui-grey-800"
    data-testid="dashboard-location-tile"
    :data-location="holding.place.location"
    :data-chain="holding.place.chain"
  >
    <div class="row-span-2 grayscale-0">
      <LocationIcon
        v-if="holding.place.location"
        :item="holding.place.location"
        icon
        size="28px"
      />
      <ChainIcon
        v-else-if="holding.place.chain"
        :chain="holding.place.chain"
        size="28px"
      />
    </div>
    <div class="flex items-center gap-1.5 min-w-0 text-xs text-rui-text-secondary">
      <span class="truncate">{{ label }}</span>
      <span
        v-if="kindMarks"
        class="inline-flex gap-0.5 shrink-0"
        data-testid="dashboard-location-tile-kinds"
      >
        <i
          v-for="part in holding.parts"
          :key="part.kind"
          class="block size-1.5 rounded-[1px]"
          :class="SOURCE_KIND_COLOR[part.kind]"
          :data-kind="part.kind"
        />
      </span>
      <slot name="badge" />
    </div>
    <div class="flex items-baseline justify-between flex-nowrap gap-x-1.5 min-w-0 font-medium">
      <span class="min-w-0 truncate">
        <FiatDisplay
          :value="holding.value"
          :loading="holding.loading"
        />
      </span>
      <PercentageDisplay
        class="shrink-0 text-xs font-normal text-rui-text-secondary"
        :value="share"
      />
    </div>
  </RouterLink>
</template>
