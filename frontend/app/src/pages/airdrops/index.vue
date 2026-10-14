<script setup lang="ts">
import { msg } from '@/message-key';
import AirdropDisplay from '@/modules/airdrops/AirdropDisplay.vue';
import PoapDeliveryAirdrops from '@/modules/airdrops/PoapDeliveryAirdrops.vue';
import { AssetAmountDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { hasDetails } from '@/pages/airdrops/airdrop-rows';
import { useAirdropsPage } from '@/pages/airdrops/use-airdrops-page';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.defi_sub.airdrops'), icon: 'lu-gift', section: 1, order: 90, drawer: 'airdrops' },
  },
});

const { t } = useI18n({ useScope: 'global' });

const {
  cols,
  expand,
  fetchAirdrops,
  fields,
  loading,
  modelExpanded,
  modelHideUnknownAlert,
  modelPagination,
  modelPillParams,
  modelSort,
  pillLabels,
  refreshTooltip,
  rows,
  status,
} = useAirdropsPage();
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.defi_sub.airdrops')]">
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            data-testid="airdrop-refresh"
            @click="fetchAirdrops()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ refreshTooltip }}
      </RuiTooltip>
    </template>

    <RuiAlert
      v-if="!modelHideUnknownAlert && status === 'unknown'"
      type="info"
      class="mb-4"
      closeable
      data-testid="airdrop-unknown-alert"
      @close="modelHideUnknownAlert = true"
    >
      {{ t('airdrops.unknown_info') }}
    </RuiAlert>

    <TableFrame>
      <template #toolbar>
        <PillFilterBar
          v-model:params="modelPillParams"
          class="flex-1 min-w-64"
          :fields="fields"
          :labels="pillLabels"
        />
      </template>
      <RuiDataTable
        v-model:pagination="modelPagination"
        v-model:expanded="modelExpanded"
        v-model:sort="modelSort"
        data-testid="airdrop-table"
        :rows="rows"
        :cols="cols"
        :loading="loading"
        single-expand
        row-attr="index"
      >
        <template #item.address="{ row }">
          <HashLink
            :text="row.address"
            location="eth"
          />
        </template>
        <template #item.amount="{ row }">
          <AssetAmountDisplay
            v-if="!hasDetails(row.details) && row.asset"
            :asset="row.asset"
            :amount="row.amount"
          />
          <ValueDisplay
            v-else-if="!hasDetails(row.details)"
            :value="row.amount"
          />
          <span v-else>{{ row.details.length }}</span>
        </template>
        <template #item.claimed="{ row: { claimed, cutoffTime, hasDecoder } }">
          <RuiTooltip
            v-if="!hasDecoder"
            :options="{ placement: 'top' }"
            :open-delay="400"
            :class-names="{ tooltip: 'max-w-48' }"
          >
            <template #activator>
              <RuiChip
                color="info"
                variant="tonal"
                size="sm"
              >
                {{ t('common.unknown') }}
              </RuiChip>
            </template>

            {{ t('airdrops.unknown_tooltip') }}
          </RuiTooltip>
          <RuiChip
            v-else-if="claimed"
            color="success"
            variant="tonal"
            size="sm"
          >
            {{ t('common.claimed') }}
          </RuiChip>
          <RuiChip
            v-else-if="cutoffTime && cutoffTime < Date.now() / 1000"
            color="grey"
            variant="tonal"
            size="sm"
          >
            {{ t('common.missed') }}
          </RuiChip>
          <RuiTooltip
            v-else
            :options="{ placement: 'top' }"
            :open-delay="400"
            :disabled="!cutoffTime"
          >
            <template #activator>
              <RuiChip
                color="primary"
                variant="tonal"
                size="sm"
                data-testid="airdrop-unclaimed"
              >
                {{ t('common.unclaimed') }}
              </RuiChip>
            </template>
            {{ t('airdrops.claim_by') }}
            <DateDisplay
              v-if="cutoffTime"
              :timestamp="cutoffTime"
            />
          </RuiTooltip>
        </template>
        <template #item.source="{ row }">
          <AirdropDisplay
            :source="row.source"
            :icon-url="row.iconUrl"
            :icon="row.icon"
          />
        </template>
        <template #item.expand="{ row }">
          <ExternalLink
            v-if="!hasDetails(row.details)"
            :url="row.link"
            custom
          >
            <RuiButton
              variant="text"
              color="primary"
              icon
            >
              <RuiIcon
                size="16"
                name="lu-external-link"
              />
            </RuiButton>
          </ExternalLink>
          <RuiTableRowExpander
            v-else
            :expanded="modelExpanded.includes(row)"
            @click="expand(row)"
          />
        </template>
        <template #expanded-item="{ row }">
          <PoapDeliveryAirdrops
            v-if="hasDetails(row.details)"
            :items="row.details"
          />
        </template>
      </RuiDataTable>
    </TableFrame>
  </TablePageLayout>
</template>
