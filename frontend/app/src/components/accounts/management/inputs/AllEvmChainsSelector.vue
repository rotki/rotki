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

const { t } = useI18n();

const emit = defineEmits<{
  (e: 'input', value: boolean): void;
}>();
</script>

<template>
  <v-sheet outlined rounded data-cy="account-all-evm-chains">
    <v-checkbox
      :input-value="value"
      :disabled="disabled"
      class="py-4 px-4 my-0"
      :label="t('address_account_form.label')"
      persistent-hint
      :hint="t('address_account_form.hint')"
      @change="emit('input', !value)"
    />
  </v-sheet>
</template>
