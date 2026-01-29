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
  <div class="flex items-center gap-1">
    <LocationIcon
      v-if="isExchangeLocation"
      icon
      :item="location"
      size="16px"
      class="mr-0.5"
    />
    <HashLink
      :text="locationLabel"
      :location="location"
      :no-scramble="isExchangeLocation"
    />
  </div>
</template>
