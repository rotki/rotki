<script setup lang="ts">
import { type DataTableHeader } from 'vuetify';
import { type ComputedRef, type Ref } from 'vue';
import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';
import { type NewDetectedToken } from '@/types/websocket-messages';
import { useMessageStore } from '@/store/message';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { uniqueStrings } from '@/utils/data';
import { getAddressFromEvmIdentifier } from '@/utils/assets';

const { tc } = useI18n();

const { tokens, removeNewDetectedTokens } = useNewlyDetectedTokens();

const mappedTokens: ComputedRef<NewDetectedToken[]> = computed(() => {
  return get(tokens).map(tokenIdentifier => ({
    tokenIdentifier,
    address: getAddressFromEvmIdentifier(tokenIdentifier)
  }));
});

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.asset'),
    value: 'tokenIdentifier'
  },
  {
    text: tc('common.address'),
    value: 'address'
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

const removeTokens = () => {
  removeNewDetectedTokens(
    get(selected).map(({ tokenIdentifier }) => tokenIdentifier)
  );

  set(selected, []);
};

const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset } = useIgnoredAssetsStore();

const ignoreTokens = async () => {
  const ids = get(selected)
    .filter(item => {
      return !get(isAssetIgnored(item.tokenIdentifier));
    })
    .map(({ tokenIdentifier }) => tokenIdentifier)
    .filter(uniqueStrings);

  if (ids.length === 0) {
    setMessage({
      success: false,
      title: tc('ignore.no_items.title', 1),
      description: tc('ignore.no_items.description', 1)
    });
    return;
  }

  const status = await ignoreAsset(ids);

  if (status.success) {
    removeTokens();
  }
};
</script>
<template>
  <card outlined-body>
    <template #title>
      {{ tc('asset_table.newly_detected.title') }}
    </template>
    <template #subtitle>
      {{ tc('asset_table.newly_detected.subtitle') }}
    </template>
    <template #actions>
      <div class="d-flex align-center">
        <div class="mr-8">
          <v-btn outlined @click="selectDeselectAllTokens">
            <v-icon>mdi-checkbox-multiple-marked-outline</v-icon>
            <span class="ml-2">
              {{ tc('asset_table.newly_detected.select_deselect_all_tokens') }}
            </span>
          </v-btn>
          <div class="d-flex mt-4">
            <div class="mr-4 mt-1">
              {{ tc('asset_table.selected', 0, { count: selected.length }) }}
            </div>
            <v-btn
              small
              text
              :disabled="selected.length === 0"
              @click="selected = []"
            >
              {{ tc('common.actions.clear_selection') }}
            </v-btn>
          </div>
        </div>
        <v-divider vertical class="mr-8" />

        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              fab
              outlined
              color="primary"
              class="mr-4"
              :disabled="selected.length === 0"
              @click="removeTokens"
              v-on="on"
            >
              <v-icon> mdi-playlist-remove </v-icon>
            </v-btn>
          </template>
          <span>{{ tc('asset_table.newly_detected.remove_from_list') }}</span>
        </v-tooltip>

        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              color="red"
              fab
              outlined
              :disabled="selected.length === 0"
              @click="ignoreTokens"
              v-on="on"
            >
              <v-icon>mdi-eye-off</v-icon>
            </v-btn>
          </template>
          <span>
            {{ tc('asset_table.newly_detected.ignore_selected') }}
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
        <hash-link :text="item.address" no-link />
      </template>
    </data-table>
  </card>
</template>
