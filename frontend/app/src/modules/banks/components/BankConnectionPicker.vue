<script setup lang="ts">
import type { BankManifest } from '@/modules/banks/types';
import { type BankSelectionOption, toBankSelectionOptions } from '@/modules/banks/bank-connection-selection';
import BankLabel from '@/modules/banks/components/BankLabel.vue';

const modelValue = defineModel<BankSelectionOption>();

const { errorMessages, manifests } = defineProps<{
  errorMessages: string[];
  manifests: BankManifest[];
}>();

const { t } = useI18n({ useScope: 'global' });

const options = computed<BankSelectionOption[]>(() =>
  toBankSelectionOptions(manifests, t('bank_settings.form.bank_other_fints')),
);
</script>

<template>
  <RuiAutoComplete
    v-model="modelValue"
    :options="options"
    :label="t('bank_settings.form.bank')"
    :placeholder="t('bank_settings.form.bank_picker_hint')"
    :error-messages="errorMessages"
    key-attr="id"
    text-attr="searchText"
    return-object
    auto-select-first
    data-testid="bank-connection-picker"
  >
    <template #selection="{ item }">
      <BankLabel
        :location="item.location"
        :name="item.name"
      />
    </template>
    <template #item="{ item }">
      <div class="flex min-w-0 flex-col py-1">
        <BankLabel
          :location="item.location"
          :name="item.name"
        />
        <span
          v-if="item.bank"
          class="truncate pl-7 text-caption text-rui-text-secondary"
        >
          {{ [
            item.bank.city,
            item.bank.bankCodes.length === 1
              ? t('bank_settings.form.bank_blz', { blz: item.bank.bankCodes[0] })
              : t('bank_settings.form.bank_blz_count', { count: item.bank.bankCodes.length }),
          ].filter(Boolean).join(' · ') }}
        </span>
        <span
          v-else-if="item.kind === 'fints-manual'"
          class="pl-7 text-caption text-rui-text-secondary"
        >
          {{ t('bank_settings.form.bank_manual_required') }}
        </span>
      </div>
    </template>
  </RuiAutoComplete>
</template>
