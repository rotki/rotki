<script setup lang="ts">
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import HashLink from '@/modules/common/links/HashLink.vue';

const props = defineProps<{
  location: string;
  locationLabel: string;
}>();

const { matchChain } = useSupportedChains();

const isExchangeLocation = computed<boolean>(() => !matchChain(props.location));
</script>

<template>
  <div class="flex items-center gap-1 min-w-0">
    <LocationIcon
      v-if="isExchangeLocation"
      icon
      :item="location"
      size="16px"
      class="mr-0.5 shrink-0"
    />
    <HashLink
      :text="locationLabel"
      :location="location"
      :no-scramble="isExchangeLocation"
      class="min-w-0"
    />
  </div>
</template>
