<script setup lang="ts">
import DetectTokensChainsSelectionItem from '@/modules/accounts/balances/DetectTokensChainsSelectionItem.vue';
import { useDetectTokenChainsSelection } from '@/modules/accounts/balances/use-detect-token-chains-selection';

const emit = defineEmits<{
  'redetect:all': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const search = ref<string>('');

const {
  detectChains,
  filtered,
  hasSelection,
  isAllSelected,
  isDetectingTokens,
  isSelected,
  reset,
  selectedCount,
  toggle,
} = useDetectTokenChainsSelection(search);

async function detectClick(chain?: string): Promise<void> {
  const isAll = await detectChains(chain);
  if (isAll) {
    emit('redetect:all');
  }
  if (!chain) {
    set(open, false);
  }
}

watch(search, () => {
  reset();
});

watch(open, (isOpen) => {
  if (!isOpen)
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
        icon
        size="xl"
        class="!outline-none rounded-none"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-chevrons-up-down"
          color="primary"
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
          @click="toggle(item.id)"
        >
          <DetectTokensChainsSelectionItem
            :item="item"
            :allow-redetect="!hasSelection"
            :detecting="isDetectingTokens"
            :enabled="isSelected(item.id)"
            @toggle="toggle(item.id)"
            @detect="detectClick(item.id)"
          />
        </div>
      </div>
      <div class="px-4 py-2 border-t border-default flex items-center justify-between">
        <RuiCheckbox
          color="primary"
          :disabled="isDetectingTokens"
          :indeterminate="hasSelection && !isAllSelected"
          :model-value="isAllSelected"
          size="sm"
          hide-details
          @click.prevent="toggle()"
        >
          {{ t('account_balances.detect_tokens.selection.select_all') }}
        </RuiCheckbox>
        <div class="flex items-center gap-2">
          <RuiButton
            v-if="hasSelection"
            variant="text"
            @click="reset()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="!hasSelection"
            :loading="isDetectingTokens"
            @click="detectClick()"
          >
            {{
              t('account_balances.detect_tokens.selection.redetect_selected', {
                length: selectedCount,
              })
            }}
          </RuiButton>
        </div>
      </div>
    </div>
  </RuiMenu>
</template>
