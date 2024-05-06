<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ExplorerUrls, explorerUrls } from '@/types/asset/asset-urls';

const additional = ['ETC'] as const;
const supportedExplorers = [...Object.values(Blockchain), ...additional];

const selection = ref<Blockchain | (typeof additional)[number]>(Blockchain.ETH);
const store = useFrontendSettingsStore();
const { explorers } = storeToRefs(store);

const address = ref<string>('');
const tx = ref<string>('');
const block = ref<string>('');

const defaultUrls: ComputedRef<ExplorerUrls> = computed(
  () => explorerUrls[get(selection)],
);

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
  <div class="explorers mt-8">
    <RuiCardHeader class="p-0">
      <template #header>
        {{ t('explorers.title') }}
      </template>
      <template #subheader>
        {{ t('explorers.subtitle') }}
      </template>
    </RuiCardHeader>

    <div class="flex flex-col gap-4 mt-6">
      <RuiMenuSelect
        v-model="selection"
        :options="supportedExplorers"
        :label="t('explorers.chain_selector')"
        :item-height="56"
        dense
        key-attr="key"
        full-width
        show-details
        variant="outlined"
        @input="onChange()"
      >
        <template #item.text="{ option }">
          <ChainDisplay
            v-if="!additional.includes(option.key)"
            dense
            :chain="option.key"
          />
          <AssetDetails
            v-else
            :asset="option.key"
            dense
          />
        </template>
        <template #activator.text="{ value }">
          <ChainDisplay
            v-if="!additional.includes(value.key)"
            dense
            :chain="value.key"
          />
          <AssetDetails
            v-else
            :asset="value.key"
            dense
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
  </div>
</template>
