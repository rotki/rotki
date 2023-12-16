<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

withDefaults(
  defineProps<{
    disabled?: boolean;
  }>(),
  {
    disabled: false,
  },
);

const { t } = useI18n();

const modelValue = defineModel<boolean>({ required: true });
</script>

<template>
  <RuiCard class="rounded">
    <label class="flex items-center gap-3 cursor-pointer">
      <RuiCheckbox
        v-model="modelValue"
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
