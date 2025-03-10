<script setup lang="ts">
import type { NewDetectedToken } from '@/types/websocket-messages';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import HashLink from '@/components/helper/HashLink.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';
import { useSpamAsset } from '@/composables/assets/spam';
import { useSupportedChains } from '@/composables/info/chains';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { arrayify } from '@/utils/array';
import { uniqueStrings } from '@/utils/data';
import { Blockchain, getAddressFromEvmIdentifier } from '@rotki/common';

interface Token extends NewDetectedToken {
  address: string;
  evmChain: Blockchain;
}

const { t } = useI18n();

const selected = ref<string[]>([]);
const sort = ref<DataTableSortData<NewDetectedToken>>();

const { removeNewDetectedTokens, tokens } = useNewlyDetectedTokens();
const { cache } = storeToRefs(useAssetCacheStore());
const { getChain } = useSupportedChains();
const { markAssetsAsSpam } = useSpamAsset();

const rows = computed<Token[]>(() => get(tokens).map((data) => {
  const evmChain = get(cache)[data.tokenIdentifier]?.evmChain;

  return {
    ...data,
    address: getAddressFromEvmIdentifier(data.tokenIdentifier),
    evmChain: evmChain ? getChain(evmChain) : Blockchain.ETH,
  };
}),
);

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
      :cols="cols"
      :rows="rows"
      :sort="sort"
      outlined
      dense
      row-attr="tokenIdentifier"
    >
      <template #item.tokenIdentifier="{ row }">
        <AssetDetails
          :asset="row.tokenIdentifier"
          opens-details
        />
      </template>

      <template #item.address="{ row }">
        <HashLink
          :chain="row.evmChain"
          :text="row.address"
          hide-alias-name
          type="token"
        />
      </template>

      <template #item.description="{ row }">
        <div v-if="row.seenDescription">
          {{ row.seenDescription }}
        </div>

        <div v-if="row.seenTxHash">
          <HashLink
            :chain="row.evmChain"
            :text="row.seenTxHash"
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
</template>
