<script setup lang="ts">
import ChainDisplay from '@/components/accounts/blockchain/ChainDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import ExplorerInput from '@/components/settings/explorers/ExplorerInput.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { type ExplorerUrls, explorerUrls } from '@/types/asset/asset-urls';
import { Blockchain } from '@rotki/common';

const extraExplorers = ['ETC'] as const;

type ExtraExplorers = (typeof extraExplorers)[number];

type SupportedExplorers = Blockchain | ExtraExplorers;

const supportedExplorers = [
  ...Object.values(Blockchain),
  ...extraExplorers,
] satisfies readonly (Blockchain | ExtraExplorers)[];

const selection = ref<SupportedExplorers>(Blockchain.ETH);
const address = ref<string>('');
const tx = ref<string>('');
const block = ref<string>('');
const token = ref<string>('');

const store = useFrontendSettingsStore();
const { explorers } = storeToRefs(store);
const { t } = useI18n();

const [CreateSelection, ReuseSelection] = createReusableTemplate<{ item: SupportedExplorers }>();

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

const tokenUrl = useValueOrDefault(
  useRefMap(userUrls, setting => setting?.token),
  useRefMap(defaultUrls, ({ token }) => token || null),
);

function onChange() {
  const setting = get(userUrls);
  set(address, setting?.address ?? '');
  set(tx, setting?.transaction ?? '');
  set(block, setting?.block ?? '');
  set(token, setting?.token ?? '');
}

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

onMounted(() => {
  onChange();
});
</script>

<template>
  <SettingsItem>
    <CreateSelection #default="{ item }">
      <ChainDisplay
        v-if="!Array.prototype.includes.call(extraExplorers, item)"
        dense
        :chain="item"
      />
      <AssetDetails
        v-else
        dense
        class="[&>div]:!py-0 -my-[0.375rem]"
        :asset="item"
      />
    </CreateSelection>

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
          <ReuseSelection :item="item" />
        </template>
        <template #selection="{ item }">
          <ReuseSelection :item="item" />
        </template>
      </RuiMenuSelect>

      <ExplorerInput
        v-model="address"
        :label="t('explorers.address')"
        :hint="t('explorers.address_url', { addressUrl })"
        :placeholder="addressUrl"
        @save-data="save('address', $event)"
      />

      <ExplorerInput
        v-if="txUrl"
        v-model="tx"
        :label="t('explorers.tx')"
        :hint="t('explorers.tx_url', { txUrl })"
        :placeholder="txUrl"
        @save-data="save('transaction', $event)"
      />

      <ExplorerInput
        v-if="blockUrl"
        v-model="block"
        :label="t('explorers.block')"
        :hint="t('explorers.block_url', { blockUrl })"
        :placeholder="blockUrl"
        @save-data="save('block', $event)"
      />

      <ExplorerInput
        v-if="tokenUrl"
        v-model="token"
        :label="t('explorers.token')"
        :hint="t('explorers.token_url', { tokenUrl })"
        :placeholder="tokenUrl"
        @save-data="save('token', $event)"
      />
    </div>
  </SettingsItem>
</template>
