<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type DataTableHeader } from '@/types/vuetify';
import { type NewDetectedToken } from '@/types/websocket-messages';

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

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.asset'),
    value: 'tokenIdentifier'
  },
  {
    text: t('common.address'),
    value: 'address'
  },
  {
    text: t('asset_table.newly_detected.seen_during'),
    value: 'description',
    sortable: false
  },
  {
    text: t('common.actions.accept'),
    value: 'accept',
    sortable: false,
    width: 0
  },
  {
    text: t('ignore_buttons.ignore'),
    value: 'ignore',
    sortable: false
  }
]);

const selected: Ref<NewDetectedToken[]> = ref([]);

const selectDeselectAllTokens = () => {
  const selectedLength = get(selected).length;
  const existLength = get(mappedTokens).length;

  if (selectedLength === existLength) {
    set(selected, []);
  } else {
    set(selected, get(mappedTokens));
  }
};

const removeTokens = (identifiers?: string[]) => {
  removeNewDetectedTokens(
    identifiers || get(selected).map(({ tokenIdentifier }) => tokenIdentifier)
  );

  set(selected, []);
};

const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset } = useIgnoredAssetsStore();

const ignoreTokens = async (identifiers?: string[]) => {
  const ids =
    identifiers ||
    get(selected)
      .filter(item => !get(isAssetIgnored(item.tokenIdentifier)))
      .map(({ tokenIdentifier }) => tokenIdentifier)
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
  <Card>
    <template #title>
      {{ t('asset_table.newly_detected.title') }}
    </template>
    <template #subtitle>
      {{ t('asset_table.newly_detected.subtitle') }}
    </template>
    <template #actions>
      <div class="flex items-center">
        <div class="mr-8">
          <RuiButton variant="outlined" @click="selectDeselectAllTokens()">
            <VIcon>mdi-checkbox-multiple-marked-outline</VIcon>
            <span class="ml-2">
              {{ t('asset_table.newly_detected.select_deselect_all_tokens') }}
            </span>
          </RuiButton>
          <div class="flex mt-4">
            <div class="mr-4 mt-1">
              {{ t('asset_table.selected', { count: selected.length }) }}
            </div>
            <RuiButton
              size="sm"
              :disabled="selected.length === 0"
              @click="selected = []"
            >
              {{ t('common.actions.clear_selection') }}
            </RuiButton>
          </div>
        </div>
        <VDivider vertical class="mr-8" />

        <VTooltip bottom>
          <template #activator="{ on }">
            <RuiButton
              variant="fab"
              color="green"
              class="mr-4"
              :disabled="selected.length === 0"
              @click="removeTokens()"
              v-on="on"
            >
              <VIcon> mdi-check </VIcon>
            </RuiButton>
          </template>
          <span>{{ t('asset_table.newly_detected.accept_selected') }}</span>
        </VTooltip>

        <VTooltip bottom>
          <template #activator="{ on }">
            <RuiButton
              color="red"
              variant="fab"
              :disabled="selected.length === 0"
              @click="ignoreTokens()"
              v-on="on"
            >
              <VIcon>mdi-eye-off</VIcon>
            </RuiButton>
          </template>
          <span>
            {{ t('asset_table.newly_detected.ignore_selected') }}
          </span>
        </VTooltip>
      </div>
    </template>
    <DataTable
      v-model="selected"
      :items="mappedTokens"
      :headers="tableHeaders"
      :single-select="false"
      item-key="tokenIdentifier"
      show-select
    >
      <template #item.tokenIdentifier="{ item }">
        <AssetDetails opens-details :asset="item.tokenIdentifier" />
      </template>

      <template #item.address="{ item }">
        <HashLink :text="item.address" :chain="item.evmChain" />
      </template>

      <template #item.description="{ item }">
        <div v-if="item.seenDescription">
          {{ item.seenDescription }}
        </div>

        <div v-if="item.seenTxHash">
          <HashLink
            type="transaction"
            :text="item.seenTxHash"
            :chain="item.evmChain"
          />
        </div>
      </template>

      <template #item.accept="{ item }">
        <RuiButton
          icon
          variant="text"
          color="green"
          @click="removeTokens([item.tokenIdentifier])"
        >
          <VIcon> mdi-check </VIcon>
        </RuiButton>
      </template>

      <template #item.ignore="{ item }">
        <RuiButton
          icon
          variant="text"
          color="red"
          @click="ignoreTokens([item.tokenIdentifier])"
        >
          <VIcon> mdi-eye-off </VIcon>
        </RuiButton>
      </template>
    </DataTable>
  </Card>
</template>
