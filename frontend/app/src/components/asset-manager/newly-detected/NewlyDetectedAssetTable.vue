<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import { type BigNumber, getAddressFromEvmIdentifier, getAddressFromSolanaIdentifier } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';
import { useSpamAsset } from '@/composables/assets/spam';
import { useSupportedChains } from '@/composables/info/chains';
import HashLink from '@/modules/common/links/HashLink.vue';
import { type NewDetectedToken, NewDetectedTokenKind } from '@/modules/messaging/types';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { arrayify } from '@/utils/array';
import { uniqueStrings } from '@/utils/data';

interface Token extends NewDetectedToken {
  address: string;
  chain: string;
  price?: BigNumber;
}

const { t } = useI18n({ useScope: 'global' });

const selected = ref<string[]>([]);
const sort = ref<DataTableSortData<NewDetectedToken>>({
  column: 'tokenIdentifier',
  direction: 'asc',
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { removeNewDetectedTokens, tokens } = useNewlyDetectedTokens();
const { cache } = storeToRefs(useAssetCacheStore());
const { getChain } = useSupportedChains();
const { markAssetsAsSpam } = useSpamAsset();
const { getAssetPrice } = usePriceUtils();

const tokenKindMapping = {
  [NewDetectedTokenKind.EVM]: {
    addressFormatter: getAddressFromEvmIdentifier,
    getChain: (data: NewDetectedToken, cacheData: ReturnType<typeof useAssetCacheStore>['cache']) => {
      const evmChain = cacheData[data.tokenIdentifier]?.evmChain;
      return evmChain ? getChain(evmChain) : data.tokenKind;
    },
  },
  [NewDetectedTokenKind.SOLANA]: {
    addressFormatter: getAddressFromSolanaIdentifier,
    getChain: (data: NewDetectedToken) => data.tokenKind,
  },
} as const;

const rows = computed<Token[]>(() => {
  const currentCache = get(cache);
  return get(tokens).map((data) => {
    const mappingEntry = tokenKindMapping[data.tokenKind];

    return {
      ...data,
      address: mappingEntry.addressFormatter(data.tokenIdentifier),
      chain: mappingEntry.getChain(data, currentCache),
      price: getAssetPrice(data.tokenIdentifier),
    };
  });
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
    sortable: true,
  },
  {
    cellClass: 'py-0',
    class: 'py-0',
    key: 'price',
    label: t('common.price'),
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

const allSelected = computed<boolean>(() => {
  const selectionLength = get(selected).length;
  return selectionLength > 0 && get(rows).length === selectionLength;
});

function toggleSelection() {
  const tokens = get(rows);
  const selectedLength = get(selected).length;
  const existLength = tokens.length;

  if (selectedLength === existLength)
    set(selected, []);

  else
    set(selected, tokens.map(({ tokenIdentifier }) => tokenIdentifier));
}

function getIdentifiers(identifiers?: string | string[]): string [] {
  return identifiers
    ? arrayify(identifiers)
    : get(selected);
}

function removeTokens(identifiers?: string | string[]): void {
  removeNewDetectedTokens(getIdentifiers(identifiers));

  set(selected, []);
}

function getUniqueIds(identifiers?: string | string[]): string[] {
  return getIdentifiers(identifiers).filter(uniqueStrings);
}

async function markAsSpam(identifiers?: string | string[]): Promise<void> {
  const ids = getUniqueIds(identifiers);

  const status = await markAssetsAsSpam(ids);

  if (status.success)
    removeTokens(ids);
}
</script>

<template>
  <TablePageLayout
    child
    hide-header
    class="lg:!-mt-5"
  >
    <RuiCard>
      <template #custom-header>
        <div class="flex gap-4 justify-between grow px-4 pt-4">
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
      </template>

      <RuiDataTable
        v-model="selected"
        v-model:sort="sort"
        :cols="cols"
        :rows="rows"
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
          <AmountDisplay
            :value="row.price"
            :asset="currencySymbol"
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
