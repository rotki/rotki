<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type NewDetectedToken } from '@/types/websocket-messages';
import type {
  DataTableColumn,
  DataTableSortColumn
} from '@rotki/ui-library-compat/dist/components';

const { t } = useI18n();

const { tokens, removeNewDetectedTokens } = useNewlyDetectedTokens();
const { cache } = storeToRefs(useAssetCacheStore());

const { getChain } = useSupportedChains();

const mappedTokens: ComputedRef<NewDetectedToken[]> = computed(() =>
  get(tokens).map(data => {
    const evmChain = get(cache)[data.tokenIdentifier]?.evmChain;

    return {
      ...data,
      address: getAddressFromEvmIdentifier(data.tokenIdentifier),
      evmChain: evmChain ? getChain(evmChain) : Blockchain.ETH
    };
  })
);

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: t('common.asset'),
    key: 'tokenIdentifier',
    sortable: true,
    cellClass: 'py-0',
    class: 'py-0'
  },
  {
    label: t('common.address'),
    key: 'address',
    sortable: true,
    cellClass: 'py-0',
    class: 'py-0'
  },
  {
    label: t('asset_table.newly_detected.seen_during'),
    key: 'description',
    cellClass: 'py-0',
    class: 'py-0'
  },
  {
    label: t('common.actions.accept'),
    key: 'accept',
    cellClass: 'py-0',
    class: 'py-0'
  },
  {
    label: t('ignore_buttons.ignore'),
    key: 'ignore',
    cellClass: 'py-0',
    class: 'py-0'
  }
]);

const selected: Ref<string[]> = ref([]);
const sort: Ref<DataTableSortColumn> = ref({
  direction: 'desc' as const
});

const selectDeselectAllTokens = () => {
  const selectedLength = get(selected).length;
  const existLength = get(mappedTokens).length;

  if (selectedLength === existLength) {
    set(selected, []);
  } else {
    set(
      selected,
      get(mappedTokens).map(({ tokenIdentifier }) => tokenIdentifier)
    );
  }
};

const removeTokens = (identifiers?: string[]) => {
  removeNewDetectedTokens(identifiers || get(selected));

  set(selected, []);
};

const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset } = useIgnoredAssetsStore();

const ignoreTokens = async (identifiers?: string[]) => {
  const ids =
    identifiers ||
    get(selected)
      .filter(tokenIdentifier => !get(isAssetIgnored(tokenIdentifier)))
      .filter(uniqueStrings);

  if (ids.length === 0) {
    setMessage({
      success: false,
      title: t('ignore.no_items.title', 1),
      description: t('ignore.no_items.description', 1)
    });
    return;
  }

  const status = await ignoreAsset(ids);

  if (status.success) {
    removeTokens(ids);
  }
};
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex flex-col sm:flex-row sm:items-center gap-4 px-4 pt-4">
        <div class="shrink-0">
          <RuiButton
            :disabled="mappedTokens.length === 0"
            variant="outlined"
            @click="selectDeselectAllTokens()"
          >
            <template #prepend>
              <RuiIcon name="checkbox-multiple-line" />
            </template>
            <span>
              {{ t('asset_table.newly_detected.select_deselect_all_tokens') }}
            </span>
          </RuiButton>
          <div class="flex mt-3">
            <div class="mr-4 mt-1">
              {{ t('asset_table.selected', { count: selected.length }) }}
            </div>
            <RuiButton
              :disabled="selected.length === 0"
              size="sm"
              variant="text"
              @click="selected = []"
            >
              {{ t('common.actions.clear_selection') }}
            </RuiButton>
          </div>
        </div>

        <div
          class="border-b sm:border-r border-gray-700 align-self-stretch sm:w-0"
        />

        <div class="flex gap-4 justify-between grow">
          <div class="flex gap-4">
            <RuiTooltip :popper="{ placement: 'bottom' }">
              <template #activator>
                <RuiButton
                  :disabled="selected.length === 0"
                  color="success"
                  icon
                  variant="outlined"
                  @click="removeTokens()"
                >
                  <RuiIcon name="check-line" />
                </RuiButton>
              </template>
              <span>{{ t('asset_table.newly_detected.accept_selected') }}</span>
            </RuiTooltip>

            <RuiTooltip :popper="{ placement: 'bottom' }">
              <template #activator>
                <RuiButton
                  :disabled="selected.length === 0"
                  color="error"
                  icon
                  variant="outlined"
                  @click="ignoreTokens()"
                >
                  <RuiIcon name="eye-off-line" />
                </RuiButton>
              </template>
              <span>
                {{ t('asset_table.newly_detected.ignore_selected') }}
              </span>
            </RuiTooltip>
          </div>

          <HintMenuIcon max-width="25rem" left>
            {{ t('asset_table.newly_detected.subtitle') }}
          </HintMenuIcon>
        </div>
      </div>
    </template>

    <RuiDataTable
      v-model="selected"
      :cols="tableHeaders"
      :rows="mappedTokens"
      :sort="sort"
      item-class="py-0"
      outlined
      row-attr="tokenIdentifier"
      @update:sort="sort = $event"
    >
      <template #item.tokenIdentifier="{ row }">
        <AssetDetails :asset="row.tokenIdentifier" opens-details />
      </template>

      <template #item.address="{ row }">
        <HashLink :chain="row.evmChain" :text="row.address" />
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

      <template #item.accept="{ row }">
        <RuiButton
          color="success"
          variant="text"
          icon
          @click="removeTokens([row.tokenIdentifier])"
        >
          <RuiIcon name="check-line" />
        </RuiButton>
      </template>

      <template #item.ignore="{ row }">
        <RuiButton
          color="error"
          variant="text"
          icon
          @click="ignoreTokens([row.tokenIdentifier])"
        >
          <RuiIcon name="eye-off-line" />
        </RuiButton>
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
