<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const { location, locationLabel, protocol } = defineProps<{
  location: string;
  locationLabel: string | null;
  protocol: string | null;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();
</script>

<template>
  <div class="flex items-center gap-2 min-w-0 text-sm">
    <LocationIcon
      :item="location"
      icon
      size="16px"
    />
    <span class="font-medium">{{ getChainName(location) }}</span>
    <span class="truncate text-xs text-rui-text-secondary">
      {{ protocol ?? t('accounting_overlay.wallet') }}
    </span>
    <span
      v-if="locationLabel"
      class="truncate text-xs text-rui-text-disabled"
    >
      {{ locationLabel }}
    </span>
  </div>
</template>
