<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import { type ExplorerUrls, explorerUrls } from '@/modules/assets/asset-urls';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import ExplorerInput from '@/modules/settings/explorers/ExplorerInput.vue';
import { useSetting } from '@/modules/settings/use-setting';
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

const explorers = useSetting('explorers');
const { updateFrontendSetting } = useSettingsOperations();
const { getChainName } = useSupportedChains();
const { t } = useI18n({ useScope: 'global' });

const [CreateSelection, ReuseSelection] = createReusableTemplate<{ item: SupportedExplorers }>();

const defaultUrls = computed<ExplorerUrls>(() => explorerUrls[get(selection)]);

const userUrls = computed(() => {
  const userExplorers = get(explorers);
  const chain = get(selection);
  return userExplorers[chain];
});

/** The chains that override at least one explorer url, in the picker's order. */
const customizedChains = computed<SupportedExplorers[]>(() => {
  const userExplorers = get(explorers);
  return supportedExplorers.filter((chain) => {
    const urls = userExplorers[chain];
    return !!urls && Object.values(urls).some(Boolean);
  });
});

const isCustomized = computed<boolean>(() => get(customizedChains).includes(get(selection)));

function chainLabel(chain: SupportedExplorers): string {
  return Array.prototype.includes.call(extraExplorers, chain) ? chain : getChainName(chain);
}

/** Under an overridden field, the url it replaced; an empty field already shows it as placeholder. */
function defaultHint(value: string, defaultUrl?: string): string {
  return value && defaultUrl ? t('explorers.default_url', { url: defaultUrl }) : '';
}

function onChange(): void {
  const setting = get(userUrls);
  set(address, setting?.address ?? '');
  set(tx, setting?.transaction ?? '');
  set(block, setting?.block ?? '');
  set(token, setting?.token ?? '');
}

function select(chain: SupportedExplorers): void {
  set(selection, chain);
  onChange();
}

async function save(type: keyof ExplorerUrls, newValue?: string): Promise<void> {
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

/** Drops every override for the selected chain, so all of its links go back to the defaults. */
async function resetChain(): Promise<void> {
  const chain = get(selection);
  const remaining = Object.fromEntries(Object.entries(get(explorers)).filter(([key]) => key !== chain));
  await updateFrontendSetting({ explorers: remaining });
  onChange();
}

onMounted(() => {
  onChange();
});
</script>

<template>
  <SettingsItem setting-key="explorers">
    <CreateSelection #default="{ item }">
      <ChainDisplay
        v-if="!Array.prototype.includes.call(extraExplorers, item)"
        :chain="item"
      />
      <AssetDetails
        v-else
        class="[&>div]:py-0! -my-1.5"
        :asset="item"
        :display="{ dense: true, size: '26px' }"
        :actions="{ hideMenu: true }"
      />
    </CreateSelection>

    <template #title>
      {{ t('explorers.title') }}
    </template>
    <template #subtitle>
      {{ t('explorers.subtitle') }}
    </template>
    <div class="flex flex-col gap-2">
      <RuiMenuSelect
        v-model="selection"
        :options="supportedExplorers"
        :label="t('explorers.chain_selector')"
        :item-height="56"
        details="hidden"
        @update:model-value="onChange()"
      >
        <template #item="{ item }">
          <div class="flex items-center justify-between gap-2 w-full">
            <ReuseSelection :item="item" />
            <span
              v-if="customizedChains.includes(item)"
              class="shrink-0 rounded-sm bg-rui-primary/10 px-1.5 text-caption-2 font-medium leading-4 tracking-normal text-rui-primary"
            >
              {{ t('explorers.custom') }}
            </span>
          </div>
        </template>
        <template #selection="{ item }">
          <ReuseSelection :item="item" />
        </template>
      </RuiMenuSelect>

      <div
        class="flex flex-wrap items-center gap-1.5 min-h-7 text-xs text-rui-text-secondary"
        data-testid="explorer-customized"
      >
        {{ t('explorers.customized') }}
        <span v-if="customizedChains.length === 0">{{ t('explorers.none') }}</span>
        <RuiChip
          v-for="chain in customizedChains"
          :key="chain"
          size="sm"
          clickable
          :color="chain === selection ? 'primary' : 'grey'"
          @click="select(chain)"
        >
          {{ chainLabel(chain) }}
        </RuiChip>
        <RuiButton
          v-if="isCustomized"
          variant="text"
          color="primary"
          size="sm"
          class="ml-auto"
          data-testid="explorer-reset"
          @click="resetChain()"
        >
          {{ t('explorers.reset') }}
        </RuiButton>
      </div>

      <div class="flex flex-col gap-1 mt-3">
        <ExplorerInput
          v-model="address"
          data-testid="explorer-address-input"
          :label="t('explorers.address')"
          :hint="defaultHint(address, defaultUrls.address)"
          :placeholder="defaultUrls.address"
          @save-data="save('address', $event)"
        />

        <ExplorerInput
          v-if="defaultUrls.transaction || tx"
          v-model="tx"
          data-testid="explorer-tx-input"
          :label="t('explorers.tx')"
          :hint="defaultHint(tx, defaultUrls.transaction)"
          :placeholder="defaultUrls.transaction"
          @save-data="save('transaction', $event)"
        />

        <ExplorerInput
          v-if="defaultUrls.block || block"
          v-model="block"
          data-testid="explorer-block-input"
          :label="t('explorers.block')"
          :hint="defaultHint(block, defaultUrls.block)"
          :placeholder="defaultUrls.block"
          @save-data="save('block', $event)"
        />

        <ExplorerInput
          v-if="defaultUrls.token || token"
          v-model="token"
          data-testid="explorer-token-input"
          :label="t('explorers.token')"
          :hint="defaultHint(token, defaultUrls.token)"
          :placeholder="defaultUrls.token"
          @save-data="save('token', $event)"
        />
      </div>
    </div>
  </SettingsItem>
</template>
