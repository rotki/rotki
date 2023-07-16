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
  <VSheet outlined rounded data-cy="account-all-evm-chains">
    <VCheckbox
      :input-value="value"
      :disabled="disabled"
      class="py-4 px-4 my-0"
      :label="t('address_account_form.label')"
      persistent-hint
      :hint="t('address_account_form.hint')"
      @change="emit('input', !value)"
    />
  </VSheet>
</template>
