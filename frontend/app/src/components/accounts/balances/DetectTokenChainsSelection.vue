<script setup lang="ts">
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useRefresh } from '@/composables/balances/refresh';
import { useSupportedChains } from '@/composables/info/chains';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const { t } = useI18n();

const open = ref<boolean>(false);
const search = ref<string>('');
const selectedChains = ref<string[]>([]);

const { isTaskRunning } = useTaskStore();
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
  if (get(isDetecting()))
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
  if (get(isDetecting()))
    return;
  const filteredVal = get(filtered);
  if (get(selectedChains).length < filteredVal.length) {
    const evmChains = filteredVal.map(item => item.id);
    set(selectedChains, evmChains);
  }
  else { reset(); }
}

async function detectClick(chain?: string) {
  if (!chain)
    set(open, false);
  const evmChains = chain ? [chain] : get(selectedChains);
  await massDetectTokens(evmChains);
}

function reset() {
  set(selectedChains, []);
}

function isDetecting(chain?: string) {
  return get(isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, chain ? { chain: get(chain) } : {}));
}

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
      <div class="p-4 border-b border-default">
        {{ t('account_balances.detect_tokens.selection.select') }}
      </div>
      <div class="h-[220px] overflow-y-auto">
        <div
          v-for="item in filtered"
          :key="item.id"
          class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 hover:dark:bg-rui-grey-900 transition"
          @click="toggleChain(item.id)"
        >
          <RuiCheckbox
            :model-value="chainIndex(item.id) > -1"
            :disabled="isDetecting()"
            color="primary"
            size="sm"
            hide-details
            @click.prevent.stop="toggleChain(item.id)"
          />
          <LocationIcon
            size="1.25"
            class="text-sm"
            :item="item.evmChainName"
            horizontal
          />
          <div class="grow" />
          <TransitionGroup
            enter-active-class="opacity-100"
            leave-active-class="opacity-0"
          >
            <RuiButton
              v-if="selectedChains.length === 0"
              variant="text"
              color="primary"
              class="flex !px-4 !py-2"
              size="sm"
              :loading="isDetecting(item.id)"
              @click.prevent.stop="detectClick(item.id)"
            >
              <div class="flex items-center gap-1.5">
                <RuiIcon
                  name="lu-refresh-ccw"
                  size="16"
                />
                {{ t('account_balances.detect_tokens.selection.redetect') }}
              </div>
            </RuiButton>
          </TransitionGroup>
        </div>
      </div>
      <div class="p-4 border-t border-default flex items-center justify-between">
        <RuiCheckbox
          color="primary"
          :disabled="isDetecting()"
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
            :loading="isDetecting()"
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
