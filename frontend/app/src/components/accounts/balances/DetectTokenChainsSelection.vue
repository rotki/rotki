<script setup lang="ts">
import DetectTokensChainsSelectionItem from '@/components/accounts/balances/DetectTokensChainsSelectionItem.vue';
import { useRefresh } from '@/composables/balances/refresh';
import { useSupportedChains } from '@/composables/info/chains';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { getTextToken } from '@rotki/common';

const emit = defineEmits<{
  'redetect:all': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const search = ref<string>('');
const selectedChains = ref<string[]>([]);

const { isTaskRunning, useIsTaskRunning } = useTaskStore();
const { txEvmChains } = useSupportedChains();
const { massDetectTokens } = useRefresh();

const filtered = computed(() => {
  const chains = [...get(txEvmChains)];
  const query = getTextToken(get(search));
  if (!query)
    return chains;

  return chains.filter(item => getTextToken(item.evmChainName).includes(query) || getTextToken(item.name).includes(query));
});

function chainIndex(chain: string) {
  return get(selectedChains).indexOf(chain);
}

function toggleChain(chain: string) {
  if (isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, { chain }))
    return;
  const chains = [...get(selectedChains)];
  const index = chainIndex(chain);
  if (index === -1)
    chains.push(chain);
  else
    chains.splice(index, 1);

  set(selectedChains, chains);
}

function toggleSelectAll() {
  if (isTaskRunning(TaskType.FETCH_DETECTED_TOKENS))
    return;
  const filteredVal = get(filtered);
  if (get(selectedChains).length < filteredVal.length) {
    const evmChains = filteredVal.map(item => item.id);
    set(selectedChains, evmChains);
  }
  else { reset(); }
}

async function detectClick(chain?: string) {
  if (chain) {
    await massDetectTokens([chain]);
  }
  else {
    set(open, false);
    const selected = get(selectedChains);
    if (selected.length === get(txEvmChains).length) {
      emit('redetect:all');
    }
    else {
      await massDetectTokens(selected);
    }
  }
}

function reset() {
  set(selectedChains, []);
}

const isDetectingTokens = useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS);

watch(search, () => {
  reset();
});

watch(open, (open) => {
  if (!open)
    reset();
});
</script>

<template>
  <RuiMenu
    v-model="open"
    :popper="{ placement: 'bottom', offsetSkid: 35 }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        class="px-3 py-3 !outline-none rounded-none"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-chevrons-up-down"
          color="primary"
          class="size-4"
        />
      </RuiButton>
    </template>

    <div class="w-[450px]">
      <div class="p-4 border-b border-default">
        <RuiTextField
          v-model="search"
          dense
          color="primary"
          variant="outlined"
          :label="t('account_balances.detect_tokens.selection.type')"
          prepend-icon="lu-search"
          hide-details
          clearable
        />
      </div>
      <div class="px-4 py-2 text-xs font-medium uppercase border-b border-default bg-rui-grey-50 dark:bg-rui-grey-900">
        {{ t('account_balances.detect_tokens.selection.select') }}
      </div>
      <div class="h-[220px] overflow-y-auto">
        <div
          v-for="item in filtered"
          :key="item.id"
          class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900 transition"
          @click="toggleChain(item.id)"
        >
          <DetectTokensChainsSelectionItem
            :item="item"
            :allow-redetect="selectedChains.length === 0"
            :detecting="isDetectingTokens"
            :enabled="chainIndex(item.id) > -1"
            @toggle="toggleChain(item.id)"
            @detect="detectClick(item.id)"
          />
        </div>
      </div>
      <div class="px-4 py-2 border-t border-default flex items-center justify-between">
        <RuiCheckbox
          color="primary"
          :disabled="isDetectingTokens"
          :indeterminate="selectedChains.length > 0 && selectedChains.length < filtered.length"
          :model-value="selectedChains.length > 0 && selectedChains.length === filtered.length"
          size="sm"
          hide-details
          @click.prevent="toggleSelectAll()"
        >
          {{ t('account_balances.detect_tokens.selection.select_all') }}
        </RuiCheckbox>
        <div class="flex items-center gap-2">
          <RuiButton
            v-if="selectedChains.length > 0"
            variant="text"
            @click="reset()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="selectedChains.length === 0"
            :loading="isDetectingTokens"
            @click="detectClick()"
          >
            {{
              t('account_balances.detect_tokens.selection.redetect_selected', {
                length: selectedChains.length,
              })
            }}
          </RuiButton>
        </div>
      </div>
    </div>
  </RuiMenu>
</template>
