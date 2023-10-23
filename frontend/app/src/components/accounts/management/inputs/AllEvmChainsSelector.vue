<script setup lang="ts">
withDefaults(
  defineProps<{
    value: boolean;
    disabled?: boolean;
  }>(),
  {
    disabled: false
  }
);

const emit = defineEmits<{
  (e: 'input', value: boolean): void;
}>();

const { t } = useI18n();
</script>

<template>
  <RuiCard class="rounded">
    <label class="flex items-center gap-3 cursor-pointer">
      <RuiCheckbox
        data-cy="account-all-evm-chains"
        class="mt-0 p-1"
        color="primary"
        :value="value"
        :disabled="disabled"
        hide-details
        @input="emit('input', !value)"
      />
      <div :class="{ 'opacity-50': disabled }">
        <div class="text-body-1">
          {{ t('address_account_form.label') }}
        </div>
        <div class="text-body-2 text-rui-text-secondary">
          {{ t('address_account_form.hint') }}
        </div>
      </div>
    </label>
  </RuiCard>
</template>
