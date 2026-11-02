<script setup lang="ts">
import { type FintsBank, fintsBanks, toFintsBankOptions } from '@/modules/banks/fints-bank-directory';

const modelValue = defineModel<FintsBank>();

const { t } = useI18n({ useScope: 'global' });

const options = computed(() => toFintsBankOptions(fintsBanks));
</script>

<template>
  <RuiAutoComplete
    v-model="modelValue"
    :options="options"
    :label="t('bank_settings.form.bank')"
    :placeholder="t('bank_settings.form.bank_picker_hint')"
    key-attr="blz"
    text-attr="searchText"
    return-object
    auto-select-first
    data-testid="fints-bank-picker"
  >
    <template #selection="{ item }">
      <div class="flex min-w-0 flex-col">
        <span class="truncate">{{ item.name }}</span>
        <span class="truncate text-caption text-rui-text-secondary">
          {{ t('bank_settings.form.bank_blz', { blz: item.blz }) }}
        </span>
      </div>
    </template>
    <template #item="{ item }">
      <div class="flex min-w-0 flex-col py-1">
        <span class="truncate">{{ item.name }}</span>
        <span class="truncate text-caption text-rui-text-secondary">
          {{ [item.city, t('bank_settings.form.bank_blz', { blz: item.blz })].filter(Boolean).join(' · ') }}
        </span>
        <span
          v-if="!item.endpoint"
          class="text-caption text-rui-warning"
        >
          {{ t('bank_settings.form.bank_manual_required') }}
        </span>
      </div>
    </template>
  </RuiAutoComplete>
</template>
