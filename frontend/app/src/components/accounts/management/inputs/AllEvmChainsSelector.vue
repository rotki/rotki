<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    value: boolean;
    disabled?: boolean;
  }>(),
  {
    disabled: false,
  },
);

const emit = defineEmits<{
  (e: 'input', value: boolean): void;
}>();

const { t } = useI18n();

const model = useSimpleVModel(props, emit);
</script>

<template>
  <RuiCard class="rounded">
    <label class="flex items-center gap-3 cursor-pointer">
      <RuiCheckbox
        v-model="model"
        data-cy="account-all-evm-chains"
        class="mt-0 p-1"
        color="primary"
        :disabled="disabled"
        hide-details
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
