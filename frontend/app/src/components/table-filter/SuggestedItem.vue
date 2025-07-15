<script setup lang="ts">
import type { Suggestion } from '@/types/filtering';
import { useTemplateRef } from 'vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { truncateAddress } from '@/utils/truncate';

const props = withDefaults(
  defineProps<{
    suggestion: Suggestion;
    chip?: boolean;
    editMode?: boolean;
  }>(),
  {
    chip: false,
    editMode: false,
  },
);

const emit = defineEmits<{
  'cancel-edit': [];
  'update:search': [value: string];
}>();

const { editMode, suggestion } = toRefs(props);

const search = ref<string>('');

const inputWidth = computed(() => Math.min(get(search).length + 2, 25));
const editInput = useTemplateRef<InstanceType<typeof HTMLInputElement>>('editInput');

const { assetInfo } = useAssetInfoRetrieval();
const { getChainName } = useSupportedChains();

const isBoolean = computed(() => {
  const item = get(suggestion);
  const value = item.value;

  return typeof value === 'boolean';
});

const asset = computed<{ identifier: string; symbol: string } | undefined>(() => {
  const item = get(suggestion);
  const value = item.value;

  if (!item.asset)
    return undefined;

  let usedAsset, identifier;
  if (typeof value === 'string') {
    identifier = value;
    usedAsset = get(assetInfo(value));
  }
  else {
    identifier = value.identifier;
    usedAsset = value;
  }

  if (!usedAsset)
    return undefined;

  let symbol = usedAsset.symbol;
  if (usedAsset.evmChain && !props.chip)
    symbol += ` (${get(getChainName(usedAsset.evmChain))})`;
  else if (usedAsset.isCustomAsset)
    symbol = usedAsset.name;

  return {
    identifier,
    symbol,
  };
});

const displayValue = computed(() => {
  const item = get(suggestion);
  const value = item.value;

  if (get(isBoolean))
    return `${value}`;

  return value;
});

const keyCodeToPropagate: string[] = ['Enter', 'Esc', 'ArrowUp', 'ArrowDown'] as const;

function onKeyDown(e: KeyboardEvent) {
  if (!keyCodeToPropagate.includes(e.code)) {
    e.stopPropagation();
  }

  if (e.code === 'Esc') {
    cancelEdit();
  }
}

function cancelEdit() {
  emit('cancel-edit');
}

watch(editMode, (curr, prev) => {
  if (curr && !prev) {
    setTimeout(() => {
      get(editInput)?.focus?.();
    }, 200);
  }
});

onClickOutside(editInput, () => {
  setTimeout(() => {
    cancelEdit();
  }, 100);
});

onBeforeUnmount(() => {
  cancelEdit();
});

watch(search, (value) => {
  emit('update:search', value);
});
</script>

<template>
  <span class="font-medium flex items-center">
    <span :class="{ 'text-rui-primary': !chip }">
      {{ suggestion.key }}
    </span>
    <template v-if="!(chip && isBoolean)">
      <span
        :class="{
          [$style.comparator]: chip,
          ['text-rui-primary']: !chip,
        }"
        class="px-1"
      >
        <span>{{ suggestion.exclude ? '!=' : '=' }}</span>
      </span>
      <input
        v-if="editMode"
        ref="editInput"
        v-model="search"
        class="edit-input border border-rui-primary-lighter outline-none px-1 h-5 rounded-sm tabular-nums bg-rui-grey-300 dark:bg-rui-grey-900"
        :style="{ width: `${inputWidth}ch` }"
        @click.prevent.stop=""
        @keydown="onKeyDown($event)"
        @keydown.esc="cancelEdit()"
      />
      <template v-else>
        <div
          v-if="suggestion.asset && asset"
          class="flex items-center gap-2"
          :class="{ 'ml-2': !chip }"
        >
          <AssetIcon
            :identifier="asset.identifier"
            padding="1.5px"
            :size="chip ? '16px' : '18px'"
            :chain-icon-size="chip ? '9px' : '11px'"
          />
          <span class="font-normal text-sm">
            {{ asset.symbol }}
          </span>
        </div>
        <span
          v-else-if="displayValue"
          class="font-normal"
        >
          {{ truncateAddress(displayValue, 10) }}
        </span>
      </template>
    </template>
  </span>
</template>

<style lang="scss" module>
.comparator {
  @apply py-0.5 border-l border-r border-white mx-1.5 flex items-center;
}

:global(.dark) {
  .comparator {
    @apply border-rui-grey-900 #{!important};
  }
}
</style>
