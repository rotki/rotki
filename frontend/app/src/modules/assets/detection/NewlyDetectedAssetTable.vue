<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { SpamPredictionToken } from '@/modules/assets/api/use-asset-spam-prediction-api';
import type { Filters } from '@/modules/assets/detection/newly-detected-filter-keys';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useNewlyDetectedFields } from '@/modules/assets/detection/use-newly-detected-fields';
import { useNewlyDetectedSelection } from '@/modules/assets/detection/use-newly-detected-selection';
import SpamAssessmentHint from '@/modules/assets/spam/SpamAssessmentHint.vue';
import { useSpamAssessments } from '@/modules/assets/spam/use-spam-assessments';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable, useTableEmptyState } from '@/modules/core/table/use-server-table';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import NewlyDetectedAssetRowActions from './NewlyDetectedAssetRowActions.vue';
import NewlyDetectedAssetToolbar from './NewlyDetectedAssetToolbar.vue';
import { type NewDetectedToken, NewDetectedTokenKind, type NewDetectedTokensRequestPayload } from './types';
import { type NewlyDetectedTokenRow, useNewlyDetectedTokenRows } from './use-newly-detected-token-rows';
import { useNewlyDetectedTokens } from './use-newly-detected-tokens';

defineOptions({
  name: 'NewlyDetectedAssetTable',
});

const { t } = useI18n({ useScope: 'global' });

const { getData, isReady } = useNewlyDetectedTokens();

const fields = useNewlyDetectedFields();

const {
  collection,
  error,
  filter,
  isLoading,
  pagination,
  refetch,
  sort,
} = useServerTable<NewDetectedToken, NewDetectedTokensRequestPayload, Filters>({
  fetch: getData,
  fields,
  sort: {
    default: {
      column: 'detectedAt',
      direction: 'desc',
    },
  },
});

const emptyState = useTableEmptyState({ error });

const pageTokens = computed<NewDetectedToken[]>(() => get(collection).data);
const spamTokens = computed<SpamPredictionToken[]>(() => get(pageTokens)
  .filter(token => token.tokenKind === NewDetectedTokenKind.EVM)
  .map(token => ({ identifier: token.tokenIdentifier, txReference: token.seenTxReference })));
const { assessments, status: spamStatus } = useSpamAssessments(spamTokens);

const cols = computed<DataTableColumn<NewlyDetectedTokenRow>[]>(() => [
  {
    // `max-w-0`: the asset takes the room left and truncates, keeping the actions on screen
    cellClass: 'py-0 max-w-0',
    class: 'py-0 w-full',
    key: 'tokenIdentifier',
    label: t('common.asset'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'address',
    label: t('common.address'),
    sortable: false,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'price',
    label: t('common.price'),
    sortable: false,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'spam',
    label: t('spam_estimate.label'),
    sortable: false,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'detectedAt',
    label: t('asset_table.newly_detected.detected_at'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'description',
    label: t('asset_table.newly_detected.seen_during'),
  },
  {
    align: 'end',
    cellClass: 'py-0 w-px',
    class: 'py-0',
    key: 'actions',
    label: t('common.actions_text'),
  },
]);

useRememberTableSorting<NewlyDetectedTokenRow>(TableId.NEWLY_DETECTED_ASSETS, sort, cols);

const rows = useNewlyDetectedTokenRows(pageTokens, assessments);

const {
  allSelected,
  markAsSpam,
  modelSelected,
  removeTokens,
  toggleSelection,
} = useNewlyDetectedSelection({
  filters: filter,
  found: (): number => get(collection).found,
  refetch,
});

watch(isReady, (ready) => {
  if (ready)
    refetch();
});

onMounted(async () => {
  await refetch();
});
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <NewlyDetectedAssetToolbar
        v-model:filters="filter"
        :all-selected="allSelected"
        :selected-count="modelSelected.length"
        :found="collection.found"
        :fields="fields"
        @toggle-selection="toggleSelection()"
        @clear-selection="modelSelected = []"
        @accept="removeTokens()"
        @mark-spam="markAsSpam()"
      />
    </template>

    <div
      v-if="spamStatus === 'unavailable'"
      class="px-4 pt-2 text-caption text-rui-warning"
    >
      {{ t('spam_estimate.unavailable_hint') }}
    </div>

    <RuiDataTable
      v-model="modelSelected"
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      :cols="cols"
      :empty="emptyState"
      :rows="rows"
      :loading="isLoading"
      dense
      row-attr="tokenIdentifier"
    >
      <template #item.tokenIdentifier="{ row }">
        <AssetDetails
          :actions="{ hideMenu: true }"
          :asset="row.tokenIdentifier"
        />
      </template>

      <template #item.address="{ row }">
        <HashLink
          :location="row.chain"
          :text="row.address"
          type="token"
        />
      </template>

      <template #item.price="{ row }">
        <FiatDisplay
          :value="row.price"
          :price-asset="row.tokenIdentifier"
        />
      </template>

      <template #item.spam="{ row }">
        <SpamAssessmentHint :assessment="row.spamAssessment" />
      </template>

      <template #item.detectedAt="{ row }">
        <DateDisplay
          :timestamp="row.detectedAt"
          milliseconds
        />
      </template>

      <template #item.description="{ row }">
        <div v-if="row.seenDescription">
          {{ row.seenDescription }}
        </div>

        <div v-if="row.seenTxReference">
          <HashLink
            :location="row.chain"
            :text="row.seenTxReference"
            type="transaction"
          />
        </div>
      </template>

      <template #item.actions="{ row }">
        <NewlyDetectedAssetRowActions
          :key="row.tokenIdentifier"
          @accept="removeTokens(row.tokenIdentifier)"
          @mark-spam="markAsSpam(row.tokenIdentifier)"
        />
      </template>
    </RuiDataTable>
  </TableFrame>
</template>
