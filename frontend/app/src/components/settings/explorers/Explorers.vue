<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import { type ExplorerUrls, explorerUrls } from '@/types/asset/asset-urls';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { useRefMap } from '@/composables/utils/useRefMap';
import ExplorerInput from '@/components/settings/explorers/ExplorerInput.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import ChainDisplay from '@/components/accounts/blockchain/ChainDisplay.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';

const additional = ['ETC'] as const;
const supportedExplorers = [...Object.values(Blockchain), ...additional];

const selection = ref<Blockchain | (typeof additional)[number]>(Blockchain.ETH);
const store = useFrontendSettingsStore();
const { explorers } = storeToRefs(store);

const address = ref<string>('');
const tx = ref<string>('');
const block = ref<string>('');

const defaultUrls = computed<ExplorerUrls>(() => explorerUrls[get(selection)]);

const userUrls = computed(() => {
  const userExplorers = get(explorers);
  const chain = get(selection);
  return userExplorers[chain];
});

const addressUrl = useValueOrDefault(
  useRefMap(userUrls, setting => setting?.address),
  useRefMap(defaultUrls, ({ address }) => address || null),
);

const txUrl = useValueOrDefault(
  useRefMap(userUrls, setting => setting?.transaction),
  useRefMap(defaultUrls, ({ transaction }) => transaction || null),
);

const blockUrl = useValueOrDefault(
  useRefMap(userUrls, setting => setting?.block),
  useRefMap(defaultUrls, ({ block }) => block || null),
);

function onChange() {
  const setting = get(userUrls);
  set(address, setting?.address ?? '');
  set(tx, setting?.transaction ?? '');
  set(block, setting?.block ?? '');
}

onMounted(() => {
  onChange();
});

async function save(type: keyof ExplorerUrls, newValue?: string) {
  const setting = get(userUrls);

  const updated = {
    ...setting,
    [type]: newValue,
  };

  if (!newValue)
    delete updated[type];

  await store.updateSetting({
    explorers: {
      ...get(explorers),
      [get(selection)]: updated,
    },
  });
}

async function saveAddress(newAddress?: string) {
  await save('address', newAddress);
}

async function saveTransaction(newTransaction?: string) {
  await save('transaction', newTransaction);
}

async function saveBlock(newBlock?: string) {
  await save('block', newBlock);
}

const { t } = useI18n();
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('explorers.title') }}
    </template>
    <template #subtitle>
      {{ t('explorers.subtitle') }}
    </template>
    <div class="flex flex-col gap-4">
      <RuiMenuSelect
        v-model="selection"
        :options="supportedExplorers"
        :label="t('explorers.chain_selector')"
        :item-height="56"
        variant="outlined"
        @update:model-value="onChange()"
      >
        <template #item="{ item }">
          <ChainDisplay
            v-if="!additional.some((chain) => chain === item)"
            dense
            :chain="item"
          />
          <AssetDetails
            v-else
            dense
            class="[&>div]:!py-0 -my-[0.375rem]"
            :asset="item"
          />
        </template>
        <template #selection="{ item }">
          <ChainDisplay
            v-if="!additional.some((chain) => chain === item)"
            dense
            :chain="item"
          />
          <AssetDetails
            v-else
            dense
            class="[&>div]:!py-0 -my-[0.375rem]"
            :asset="item"
          />
        </template>
      </RuiMenuSelect>

      <ExplorerInput
        v-model="address"
        :label="t('explorers.address')"
        :hint="t('explorers.address_url', { addressUrl })"
        :placeholder="addressUrl"
        @save-data="saveAddress($event)"
      />
      <ExplorerInput
        v-if="txUrl"
        v-model="tx"
        :label="t('explorers.tx')"
        :hint="t('explorers.tx_url', { txUrl })"
        :placeholder="txUrl"
        @save-data="saveTransaction($event)"
      />
      <ExplorerInput
        v-if="blockUrl"
        v-model="block"
        :label="t('explorers.block')"
        :hint="t('explorers.block_url', { blockUrl })"
        :placeholder="blockUrl"
        @save-data="saveBlock($event)"
      />
    </div>
  </SettingsItem>
</template>
