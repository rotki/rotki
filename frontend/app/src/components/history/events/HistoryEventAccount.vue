<script setup lang="ts">
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import HashLink from '@/modules/common/links/HashLink.vue';

const props = defineProps<{
  location: string;
  locationLabel: string;
  dense?: boolean
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
      :class="{ '!text-[10px]': dense }"
    />
    <HashLink
      :text="locationLabel"
      :location="location"
      :no-scramble="isExchangeLocation"
      class="min-w-0"
      :class="{ '!text-[10px]': dense }"
    />
  </div>
</template>
