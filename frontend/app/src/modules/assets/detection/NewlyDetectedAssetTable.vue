<script setup lang="ts">
import type { NewDetectedToken, NewDetectedTokensRequestPayload } from './types';
import type { Filters } from '@/modules/assets/detection/newly-detected-filter-keys';
import { RuiDataTable } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useNewlyDetectedFields } from '@/modules/assets/detection/use-newly-detected-fields';
import { useNewlyDetectedSelection } from '@/modules/assets/detection/use-newly-detected-selection';
import SpamAssessmentHint from '@/modules/assets/spam/SpamAssessmentHint.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useServerTable, useTableEmptyState } from '@/modules/core/table/use-server-table';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import NewlyDetectedAssetRowActions from './NewlyDetectedAssetRowActions.vue';
import NewlyDetectedAssetToolbar from './NewlyDetectedAssetToolbar.vue';
import { useNewlyDetectedColumns } from './use-newly-detected-columns';
import { useNewlyDetectedPageRows } from './use-newly-detected-page-rows';
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
const { rows, spamStatus } = useNewlyDetectedPageRows(pageTokens);

const cols = useNewlyDetectedColumns(sort);

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
