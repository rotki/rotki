<script setup lang="ts">
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { compact = false, location, locationLabel = null } = defineProps<{
  compact?: boolean;
  location: string;
  locationLabel?: string | null;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useLocationData } = useLocations();
const { matchChain } = useSupportedChains();
const locationData = useLocationData(() => location);

/** Only a blockchain account's label is an address; an exchange or import label is a plain name. */
const isChainAccount = computed<boolean>(() => matchChain(location) !== undefined);
const locationName = computed<string>(() => get(locationData)?.name ?? location);
</script>

<template>
  <span :class="compact ? 'font-medium text-rui-text' : 'font-semibold text-rui-text'">
    {{ locationName }}
  </span>
  <HashLink
    v-if="locationLabel && isChainAccount"
    :text="locationLabel"
    :location="location"
    :size="compact ? '12' : undefined"
    :reveal-actions="!compact"
  />
  <span
    v-else-if="locationLabel"
    class="text-rui-text-secondary"
    data-testid="reconciliation-account-label"
  >
    {{ locationLabel }}
  </span>
  <span
    v-else
    class="text-rui-text-secondary"
  >
    {{ t('data_issues.reconciliation.no_account_label') }}
  </span>
</template>
