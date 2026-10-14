<script setup lang="ts">
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import AssetBalancesSkeleton from '@/modules/balances/AssetBalancesSkeleton.vue';
import LocationAssetsEmpty from '@/modules/balances/LocationAssetsEmpty.vue';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useLocationBalanceStatus } from '@/modules/balances/use-location-balance-status';
import { useLocations } from '@/modules/core/common/use-locations';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import TableSearchField from '@/modules/core/table/TableSearchField.vue';

const { identifier } = defineProps<{
  identifier: string;
}>();

const search = ref<string>('');

const { t } = useI18n({ useScope: 'global' });

const { useLocationBreakdown } = useAggregatedBalances();
const locationBreakdown = useLocationBreakdown(() => identifier);

const { useLocationData } = useLocations();
const location = useLocationData(() => identifier);

const { isInitialLoading, isRefreshing } = useLocationBalanceStatus(identifier);

const hasRows = computed<boolean>(() => get(locationBreakdown).length > 0);

const isEmpty = computed<boolean>(() => !get(isInitialLoading) && !get(hasRows));
</script>

<template>
  <section class="flex flex-col gap-3">
    <h2 class="text-base font-semibold text-rui-text">
      {{ t('common.assets') }}
    </h2>
    <LocationAssetsEmpty
      v-if="isEmpty"
      :identifier="identifier"
      :name="location?.name ?? identifier"
    />
    <TableFrame v-else>
      <template #toolbar>
        <div
          v-if="isRefreshing"
          class="flex items-center gap-2 text-sm text-rui-text-secondary"
          data-testid="location-assets-refreshing"
        >
          <RuiProgress
            variant="indeterminate"
            color="primary"
            size="16"
            thickness="2"
            circular
          />
          {{ t('locations.refreshing') }}
        </div>
        <TableSearchField v-model="search" />
      </template>
      <AssetBalances
        v-if="hasRows"
        v-model:search="search"
        :balances="locationBreakdown"
        :breakdown="{ hide: true }"
        sticky-header
      />
      <AssetBalancesSkeleton v-else />
    </TableFrame>
  </section>
</template>
