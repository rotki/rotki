<script setup lang="ts">
import type { BankConnectionIdentity } from '@/modules/banks/types';
import { getTextToken } from '@rotki/common';
import { isEqual, sortBy } from 'es-toolkit';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';

const modelValue = defineModel<BankConnectionIdentity[]>({ required: true });
const search = defineModel<string>('search', { required: true });

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ 'update:all-selected': [allSelected: boolean] }>();

const { t } = useI18n({ useScope: 'global' });

const { connections } = storeToRefs(useBankConnectionsStore());

const banks = computed<BankConnectionIdentity[]>(() =>
  get(connections).map(({ connector, name }) => ({ connector, name })),
);

const filteredBanks = computed<BankConnectionIdentity[]>(() => {
  const query = getTextToken(get(search));
  return get(banks).filter(bank =>
    getTextToken(bank.name).includes(query) || getTextToken(bank.connector).includes(query),
  );
});

function isSelected(bank: BankConnectionIdentity): boolean {
  return get(modelValue).some(item => item.connector === bank.connector && item.name === bank.name);
}

function toggleSelect(bank: BankConnectionIdentity): void {
  const model = get(modelValue);
  if (isSelected(bank))
    updateSelection(model.filter(item => !(item.connector === bank.connector && item.name === bank.name)));
  else
    updateSelection([...model, bank]);
}

function toggleSelectAll(): void {
  updateSelection(get(modelValue).length > 0 ? [] : get(banks));
}

function updateSelection(selection: BankConnectionIdentity[]): void {
  set(modelValue, selection);
  emit('update:all-selected', isEqual(
    sortBy(selection, ['connector', 'name']),
    sortBy(get(banks), ['connector', 'name']),
  ));
}

defineExpose({
  toggleSelectAll,
});
</script>

<template>
  <div
    v-for="bank in filteredBanks"
    :key="`${bank.connector}#${bank.name}`"
    class="flex items-center px-4 py-1 pr-2 cursor-pointer hover:bg-rui-grey-100 dark:hover:bg-rui-grey-900 transition"
    data-testid="refresh-bank-row"
    @click="toggleSelect(bank)"
  >
    <RuiCheckbox
      :model-value="isSelected(bank)"
      :disabled="processing"
      color="primary"
      size="sm"
      details="hidden"
      @click.prevent
    />

    <LocationDisplay
      identifier="banks"
      icon
      :open-details="false"
      size="20px"
    />

    <span class="ml-2 text-rui-text-secondary text-sm">
      {{ bank.name }}
    </span>

    <div class="grow" />
  </div>

  <div
    v-if="banks.length === 0"
    class="px-4 py-2 text-xs text-rui-text-secondary italic"
  >
    {{ t('history_refresh_selection.no_banks') }}
  </div>
</template>
