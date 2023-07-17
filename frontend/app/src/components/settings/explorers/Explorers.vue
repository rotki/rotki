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
  () => explorerUrls[get(selection)]
);

const userUrls = computed(() => {
  const userExplorers = get(explorers);
  const chain = get(selection);
  return userExplorers[chain];
});

const addressUrl = useValueOrDefault(
  useRefMap(userUrls, setting => setting?.address),
  useRefMap(defaultUrls, ({ address }) => address || null)
);

const txUrl = useValueOrDefault(
  useRefMap(userUrls, setting => setting?.transaction),
  useRefMap(defaultUrls, ({ transaction }) => transaction || null)
);

const blockUrl = useValueOrDefault(
  useRefMap(userUrls, setting => setting?.block),
  useRefMap(defaultUrls, ({ block }) => block || null)
);

const onChange = () => {
  const setting = get(userUrls);
  set(address, setting?.address ?? '');
  set(tx, setting?.transaction ?? '');
  set(block, setting?.block ?? '');
};

onMounted(() => {
  onChange();
});

const isValid = (entry: string | null): boolean =>
  !entry ? false : entry.length > 0;

const save = async (type: keyof ExplorerUrls, newValue?: string) => {
  const setting = get(userUrls);

  const updated = {
    ...setting,
    [type]: newValue
  };

  if (!newValue) {
    delete updated[type];
  }

  await store.updateSetting({
    explorers: {
      ...get(explorers),
      [get(selection)]: updated
    }
  });
};

const saveAddress = async (newAddress?: string) => {
  await save('address', newAddress);
};

const saveTransaction = async (newTransaction?: string) => {
  await save('transaction', newTransaction);
};

const saveBlock = async (newBlock?: string) => {
  await save('block', newBlock);
};

const { t } = useI18n();
</script>

<template>
  <div class="explorers mt-8">
    <div class="text-h6">
      {{ t('explorers.title') }}
    </div>
    <div class="text-subtitle-1">
      {{ t('explorers.subtitle') }}
    </div>

    <VSelect
      v-model="selection"
      class="mt-4"
      outlined
      :items="supportedExplorers"
      :label="t('explorers.chain_selector')"
      @change="onChange()"
    >
      <template #item="{ item }">
        <ChainDisplay v-if="!additional.includes(item)" :chain="item" />
        <AssetDetails v-else :asset="item" />
      </template>
      <template #selection="{ item }">
        <ChainDisplay v-if="!additional.includes(item)" :chain="item" />
        <AssetDetails v-else :asset="item" />
      </template>
    </VSelect>

    <VTextField
      v-model="address"
      outlined
      clearable
      :label="t('explorers.address')"
      :hint="t('explorers.address_url', { addressUrl })"
      :placeholder="addressUrl"
      persistent-hint
      @click:clear="saveAddress()"
    >
      <template #append-outer>
        <VBtn
          icon
          :disabled="!isValid(address)"
          class="mt-n2"
          @click="saveAddress(address)"
        >
          <VIcon>mdi-content-save</VIcon>
        </VBtn>
      </template>
    </VTextField>
    <VTextField
      v-if="txUrl"
      v-model="tx"
      outlined
      clearable
      :label="t('explorers.tx')"
      :hint="t('explorers.tx_url', { txUrl })"
      :placeholder="txUrl"
      persistent-hint
      @click:clear="saveTransaction()"
    >
      <template #append-outer>
        <VBtn
          icon
          :disabled="!isValid(tx)"
          class="mt-n2"
          @click="saveTransaction(tx)"
        >
          <VIcon>mdi-content-save</VIcon>
        </VBtn>
      </template>
    </VTextField>
    <VTextField
      v-if="blockUrl"
      v-model="block"
      outlined
      clearable
      :label="t('explorers.block')"
      :hint="t('explorers.block_url', { blockUrl })"
      :placeholder="blockUrl"
      persistent-hint
      @click:clear="saveBlock()"
    >
      <template #append-outer>
        <VBtn
          icon
          :disabled="!isValid(block)"
          class="mt-n2"
          @click="saveBlock(block)"
        >
          <VIcon>mdi-content-save</VIcon>
        </VBtn>
      </template>
    </VTextField>
  </div>
</template>

<style scoped lang="scss">
.explorers {
  :deep(.v-input) {
    .v-input {
      &__icon {
        &--append {
          padding-top: 1rem;
        }
      }
    }
  }
}
</style>
