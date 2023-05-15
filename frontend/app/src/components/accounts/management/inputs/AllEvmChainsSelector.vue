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

const { tc } = useI18n();

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
      :label="tc('address_account_form.label')"
      persistent-hint
      :hint="tc('address_account_form.hint')"
      @change="emit('input', !value)"
    />
  </v-sheet>
</template>
