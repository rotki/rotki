<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { location } = defineProps<{
  location: string;
  locationLabel: string;
  dense?: boolean;
  /** Hides the copy and explorer buttons until the link or its `group/row` is hovered or focused. */
  revealActions?: boolean;
}>();

const { matchChain } = useSupportedChains();

const isExchangeLocation = computed<boolean>(() => !matchChain(location));
</script>

<template>
  <div class="flex items-center gap-1 min-w-0">
    <LocationIcon
      v-if="isExchangeLocation"
      icon
      :item="location"
      size="16px"
      class="mr-0.5 shrink-0"
      :class="{ 'text-[10px]!': dense }"
    />
    <HashLink
      :text="locationLabel"
      :location="location"
      :no-scramble="isExchangeLocation"
      :reveal-actions="revealActions"
      class="min-w-0"
      :class="{ 'text-[10px]!': dense }"
    />
  </div>
</template>
