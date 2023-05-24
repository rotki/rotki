<script setup lang="ts">
import { type DataTableHeader } from 'vuetify';
import { type ComputedRef, type Ref } from 'vue';
import { Blockchain } from '@rotki/common/lib/blockchain';
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
  <card outlined-body>
    <template #title>
      {{ t('asset_table.newly_detected.title') }}
    </template>
    <template #subtitle>
      {{ t('asset_table.newly_detected.subtitle') }}
    </template>
    <template #actions>
      <div class="d-flex align-center">
        <div class="mr-8">
          <v-btn outlined @click="selectDeselectAllTokens()">
            <v-icon>mdi-checkbox-multiple-marked-outline</v-icon>
            <span class="ml-2">
              {{ t('asset_table.newly_detected.select_deselect_all_tokens') }}
            </span>
          </v-btn>
          <div class="d-flex mt-4">
            <div class="mr-4 mt-1">
              {{ t('asset_table.selected', { count: selected.length }) }}
            </div>
            <v-btn
              small
              text
              :disabled="selected.length === 0"
              @click="selected = []"
            >
              {{ t('common.actions.clear_selection') }}
            </v-btn>
          </div>
        </div>
        <v-divider vertical class="mr-8" />

        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              fab
              outlined
              color="green"
              class="mr-4"
              :disabled="selected.length === 0"
              @click="removeTokens()"
              v-on="on"
            >
              <v-icon> mdi-check </v-icon>
            </v-btn>
          </template>
          <span>{{ t('asset_table.newly_detected.accept_selected') }}</span>
        </v-tooltip>

        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              color="red"
              fab
              outlined
              :disabled="selected.length === 0"
              @click="ignoreTokens()"
              v-on="on"
            >
              <v-icon>mdi-eye-off</v-icon>
            </v-btn>
          </template>
          <span>
            {{ t('asset_table.newly_detected.ignore_selected') }}
          </span>
        </v-tooltip>
      </div>
    </template>
    <data-table
      v-model="selected"
      :items="mappedTokens"
      :headers="tableHeaders"
      :single-select="false"
      item-key="tokenIdentifier"
      show-select
    >
      <template #item.tokenIdentifier="{ item }">
        <asset-details opens-details :asset="item.tokenIdentifier" />
      </template>

      <template #item.address="{ item }">
        <hash-link :text="item.address" :chain="item.evmChain" />
      </template>

      <template #item.description="{ item }">
        <div v-if="item.seenDescription">
          {{ item.seenDescription }}
        </div>

        <div v-if="item.seenTxHash">
          <hash-link
            type="transaction"
            :text="item.seenTxHash"
            :chain="item.evmChain"
          />
        </div>
      </template>

      <template #item.accept="{ item }">
        <v-btn icon color="green" @click="removeTokens([item.tokenIdentifier])">
          <v-icon> mdi-check </v-icon>
        </v-btn>
      </template>

      <template #item.ignore="{ item }">
        <v-btn icon color="red" @click="ignoreTokens([item.tokenIdentifier])">
          <v-icon> mdi-eye-off </v-icon>
        </v-btn>
      </template>
    </data-table>
  </card>
</template>
