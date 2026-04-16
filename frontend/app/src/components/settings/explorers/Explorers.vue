<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import ChainDisplay from '@/components/accounts/blockchain/ChainDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import ExplorerInput from '@/components/settings/explorers/ExplorerInput.vue';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { type ExplorerUrls, explorerUrls } from '@/modules/assets/asset-urls';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

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
const { updateFrontendSetting } = useSettingsOperations();
const { t } = useI18n({ useScope: 'global' });

const [CreateSelection, ReuseSelection] = createReusableTemplate<{ item: SupportedExplorers }>();

const defaultUrls = computed<ExplorerUrls>(() => explorerUrls[get(selection)]);

const userUrls = computed(() => {
  const userExplorers = get(explorers);
  const chain = get(selection);
  return userExplorers[chain];
});

const addressUrl = useValueOrDefault(
  () => get(userUrls)?.address,
  () => get(defaultUrls).address || null,
);

const txUrl = useValueOrDefault(
  () => get(userUrls)?.transaction,
  () => get(defaultUrls).transaction || null,
);

const blockUrl = useValueOrDefault(
  () => get(userUrls)?.block,
  () => get(defaultUrls).block || null,
);

const tokenUrl = useValueOrDefault(
  () => get(userUrls)?.token,
  () => get(defaultUrls).token || null,
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

  await updateFrontendSetting({
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
        :chain="item"
      />
      <AssetDetails
        v-else
        dense
        size="26px"
        class="[&>div]:!py-0 -my-[0.375rem]"
        :asset="item"
        hide-menu
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
