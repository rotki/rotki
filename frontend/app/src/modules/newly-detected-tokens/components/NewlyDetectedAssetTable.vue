<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import { type BigNumber, getAddressFromEvmIdentifier, getAddressFromSolanaIdentifier } from '@rotki/common';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useSpamAsset } from '@/composables/assets/spam';
import { useSupportedChains } from '@/composables/info/chains';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { FiatDisplay } from '@/modules/amount-display/components';
import HashLink from '@/modules/common/links/HashLink.vue';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { arrayify } from '@/utils/array';
import { uniqueStrings } from '@/utils/data';
import { type NewDetectedToken, NewDetectedTokenKind } from '../types';
import { useNewlyDetectedTokens } from '../use-newly-detected-tokens';

defineOptions({
  name: 'NewlyDetectedAssetTable',
});

interface Token extends NewDetectedToken {
  address: string;
  chain: string;
  price?: BigNumber;
}

const TOKEN_KIND_MAPPING = {
  [NewDetectedTokenKind.EVM]: {
    addressFormatter: getAddressFromEvmIdentifier,
  },
  [NewDetectedTokenKind.SOLANA]: {
    addressFormatter: getAddressFromSolanaIdentifier,
  },
} as const;

const { t } = useI18n({ useScope: 'global' });

const selected = ref<string[]>([]);
const tokenKindFilter = ref<NewDetectedTokenKind>();

const { cache } = storeToRefs(useAssetCacheStore());

const { getAllIdentifiers, getData, isReady, removeNewDetectedTokens } = useNewlyDetectedTokens();
const { getChain } = useSupportedChains();
const { markAssetsAsSpam } = useSpamAsset();
const { getAssetPrice } = usePriceUtils();

const {
  fetchData,
  isLoading,
  pagination,
  sort,
  state,
} = usePaginationFilters<NewDetectedToken>(getData, {
  defaultSortBy: {
    column: 'detectedAt',
    direction: 'desc',
  },
  extraParams: computed(() => ({
    tokenKind: get(tokenKindFilter),
  })),
});

const cols = computed<DataTableColumn<Token>[]>(() => [
  {
    cellClass: 'py-0',
    class: 'py-0',
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
    align: 'center',
    cellClass: 'py-0',
    class: 'py-0',
    key: 'actions',
    label: t('common.actions_text'),
  },
]);

useRememberTableSorting<Token>(TableId.NEWLY_DETECTED_ASSETS, sort, cols);

const rows = computed<Token[]>(() => {
  const currentCache = get(cache);
  return get(state).data.map((data) => {
    const evmChain = currentCache[data.tokenIdentifier]?.evmChain;
    const chain = data.tokenKind === NewDetectedTokenKind.EVM && evmChain
      ? getChain(evmChain)
      : data.tokenKind;

    return {
      ...data,
      address: TOKEN_KIND_MAPPING[data.tokenKind].addressFormatter(data.tokenIdentifier),
      chain,
      price: getAssetPrice(data.tokenIdentifier),
    };
  });
});

const allSelected = computed<boolean>(() => {
  const selectionLength = get(selected).length;
  const totalFiltered = get(state).found;
  return selectionLength > 0 && totalFiltered === selectionLength;
});

const tokenKindOptions = computed<{ title: string; value: NewDetectedTokenKind | undefined }[]>(() => [
  { title: t('asset_table.newly_detected.all_types'), value: undefined },
  { title: 'EVM', value: NewDetectedTokenKind.EVM },
  { title: 'Solana', value: NewDetectedTokenKind.SOLANA },
]);

async function toggleSelection(): Promise<void> {
  const selectedLength = get(selected).length;
  const allIdentifiers = await getAllIdentifiers(get(tokenKindFilter));

  if (selectedLength === allIdentifiers.length)
    set(selected, []);
  else
    set(selected, allIdentifiers);
}

function getIdentifiers(identifiers?: string | string[]): string[] {
  return identifiers
    ? arrayify(identifiers)
    : get(selected);
}

function getUniqueIds(identifiers?: string | string[]): string[] {
  return getIdentifiers(identifiers).filter(uniqueStrings);
}

async function removeTokens(identifiers?: string | string[]): Promise<void> {
  await removeNewDetectedTokens(getIdentifiers(identifiers));
  set(selected, []);
  await fetchData();
}

async function markAsSpam(identifiers?: string | string[]): Promise<void> {
  const ids = getUniqueIds(identifiers);

  const status = await markAssetsAsSpam(ids);

  if (status.success)
    await removeTokens(ids);
}

watch(isReady, (ready) => {
  if (ready)
    fetchData();
});

watch(tokenKindFilter, () => {
  set(selected, []);
});

onMounted(async () => {
  await fetchData();
});
</script>

<template>
  <TablePageLayout
    child
    hide-header
    class="lg:!-mt-5"
  >
    <RuiCard>
      <template #custom-header>
        <div class="flex flex-col gap-4 px-4 pt-4">
          <div class="flex gap-4 justify-between grow">
            <div class="flex gap-4 content-center">
              <RuiTooltip
                :popper="{ placement: 'bottom' }"
                :open-delay="500"
              >
                <template #activator>
                  <RuiCheckbox
                    color="primary"
                    hide-details
                    size="sm"
                    class="ms-4 mt-1 text-body-2"
                    :model-value="allSelected"
                    @update:model-value="toggleSelection()"
                  >
                    {{ t('asset_table.selected', { count: selected.length }) }}
                  </RuiCheckbox>
                </template>
                {{ t('asset_table.newly_detected.select_deselect_all_tokens') }}
              </RuiTooltip>

              <div>
                <RuiTooltip
                  :popper="{ placement: 'bottom' }"
                  :open-delay="500"
                >
                  <template #activator>
                    <RuiButton
                      :disabled="selected.length === 0"
                      color="success"
                      variant="text"
                      class="w-12 h-12"
                      @click="removeTokens()"
                    >
                      <RuiIcon name="lu-check" />
                    </RuiButton>
                  </template>

                  {{ t('asset_table.newly_detected.accept_selected') }}
                </RuiTooltip>

                <RuiTooltip
                  :popper="{ placement: 'bottom' }"
                  :open-delay="500"
                >
                  <template #activator>
                    <RuiButton
                      :disabled="selected.length === 0"
                      color="error"
                      variant="text"
                      class="w-12 h-12"
                      @click="markAsSpam()"
                    >
                      <RuiIcon name="lu-octagon-alert" />
                    </RuiButton>
                  </template>

                  {{ t('asset_table.newly_detected.mark_selected_as_spam') }}
                </RuiTooltip>
              </div>
            </div>

            <HintMenuIcon :popper="{ placement: 'left-start' }">
              {{ t('asset_table.newly_detected.subtitle') }}
            </HintMenuIcon>
          </div>

          <!-- Filters -->
          <div class="flex gap-4 items-center">
            <RuiMenuSelect
              v-model="tokenKindFilter"
              :options="tokenKindOptions"
              :label="t('asset_table.newly_detected.token_type')"
              key-attr="value"
              text-attr="title"
              variant="outlined"
              dense
              hide-details
              class="max-w-[180px]"
            />
          </div>
        </div>
      </template>

      <RuiDataTable
        v-model="selected"
        v-model:sort.external="sort"
        v-model:pagination.external="pagination"
        :cols="cols"
        :rows="rows"
        :loading="isLoading"
        outlined
        dense
        row-attr="tokenIdentifier"
      >
        <template #item.tokenIdentifier="{ row }">
          <AssetDetails
            hide-menu
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
          <RuiButtonGroup
            :key="row.tokenIdentifier"
            class="dark:!divide-rui-grey-800"
          >
            <RuiTooltip
              :open-delay="300"
              :close-delay="0"
            >
              <template #activator>
                <RuiButton
                  color="success"
                  icon
                  variant="text"
                  class="m-auto !rounded-none"
                  @click="removeTokens(row.tokenIdentifier)"
                >
                  <RuiIcon name="lu-check" />
                </RuiButton>
              </template>
              {{ t('asset_table.newly_detected.accept') }}
            </RuiTooltip>
            <RuiTooltip
              :open-delay="300"
              :close-delay="0"
            >
              <template #activator>
                <RuiButton
                  color="error"
                  icon
                  variant="text"
                  class="m-auto !rounded-none"
                  @click="markAsSpam(row.tokenIdentifier)"
                >
                  <RuiIcon name="lu-octagon-alert" />
                </RuiButton>
              </template>
              {{ t('asset_table.newly_detected.mark_as_spam') }}
            </RuiTooltip>
          </RuiButtonGroup>
        </template>
      </RuiDataTable>
    </RuiCard>
  </TablePageLayout>
</template>
