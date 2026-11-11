<script setup lang="ts" generic="TClear = undefined, TClearable extends boolean = false">
import type { ClearedValue, RuiAutoComplete } from '@rotki/ui-library';
import type { ChainInfo } from '@/modules/core/api/types/chains';
import type { ForwardedProps, UnexportedAutoCompleteProps } from '@/modules/core/common/forwarded-props';
import { Blockchain } from '@rotki/common';
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import { toClearedValue } from '@/modules/core/common/cleared-value';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getModuleEnabled, Module } from '@/modules/session/use-module-enabled';

interface Props {
  dense?: boolean;
  evmOnly?: boolean;
  excludeEthStaking?: boolean;
  items?: string[];
  /**
   * Shows the clear button, so the update can carry `valueOnClear`.
   *
   * @remarks
   * Typed `& boolean` so the compiler emits a Boolean prop: a bare type parameter compiles to an
   * untyped one, and a bare `clearable` attribute would then arrive as a falsy `''`.
   */
  clearable?: TClearable & boolean;
  /** What clearing writes, `undefined` when not given; `''` keeps a `string` model exact. */
  valueOnClear?: TClear;
  /** The picked chain. Not a `defineModel`, since the update is typed apart from the prop. */
  modelValue: string | NoInfer<TClear>;
}

defineOptions({
  inheritAttrs: false,
});

const {
  clearable,
  dense = false,
  evmOnly = false,
  excludeEthStaking = false,
  items = [],
  modelValue,
  valueOnClear,
} = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiAutoComplete<string, ChainInfo>, Props & UnexportedAutoCompleteProps>>();

const emit = defineEmits<{
  'update:model-value': [value: string | ClearedValue<string, TClear, TClearable>];
}>();

const { isEvm, supportedChains } = useSupportedChains();

const { t } = useI18n({ useScope: 'global' });

const filteredItems = computed<string[]>(() => {
  const isEth2Enabled = getModuleEnabled(Module.ETH2);

  let data: string[] = get(supportedChains).map(({ id }) => id);

  if (items.length > 0)
    data = data.filter(chain => items.includes(chain));

  if (!isEth2Enabled || excludeEthStaking)
    data = data.filter(symbol => symbol !== Blockchain.ETH2);

  if (evmOnly)
    data = data.filter(isEvm);

  return data;
});

const mappedOptions = computed<ChainInfo[]>(() => {
  const filtered = get(filteredItems);
  const chains = get(supportedChains)
    .filter(item => filtered.includes(item.id))
    .sort((a, b) => a.name.localeCompare(b.name));

  if (items.includes('all')) {
    chains.unshift({
      id: 'all',
      image: '',
      name: t('account_form.labels.all_supported_chains'),
      type: 'all',
    });
  }

  return chains;
});

/** "All supported chains" sits apart, above a "Chains" header, so it doesn't read as one more chain. */
const groupBy = computed<((item: ChainInfo) => string) | undefined>(() => {
  if (!items.includes('all'))
    return undefined;
  return (item: ChainInfo): string => (item.id === 'all' ? '' : t('common.chain'));
});

/** The chain the field shows; a clear value that is not a chain reads as none. */
const selected = computed<string | undefined>(() => (typeof modelValue === 'string' ? modelValue : undefined));

/** A picked chain goes up as is; a cleared field sends the caller's `valueOnClear`. */
function onUpdateModelValue(value: string | undefined): void {
  emit('update:model-value', value ?? toClearedValue<string, TClear, TClearable>(valueOnClear));
}
</script>

<template>
  <RuiAutoComplete
    :model-value="selected"
    :clearable="clearable"
    :dense="dense"
    :options="mappedOptions"
    :label="t('account_form.labels.blockchain')"
    data-testid="account-blockchain-field"
    auto-select-first
    text-attr="name"
    :item-height="dense ? 40 : 48"
    :group-by="groupBy"
    :class-names="{ menu: 'max-h-96' }"
    v-bind="{ ...$attrs, keyAttr: 'id' as any }"
    @update:model-value="onUpdateModelValue($event)"
  >
    <template #group-header="{ group }">
      <div
        v-if="group"
        class="px-3 pt-3 pb-1 text-xs font-medium text-rui-text-secondary border-t border-rui-divider"
      >
        {{ group }}
      </div>
    </template>
    <template #selection="{ item }">
      <ChainDisplay
        :class="{ '-my-1': dense }"
        :dense="dense"
        :chain="item.id"
      />
    </template>
    <template #item="{ item }">
      <ChainDisplay
        :class="{ 'my-1': dense }"
        :dense="dense"
        :chain="item.id"
      />
    </template>
  </RuiAutoComplete>
</template>
