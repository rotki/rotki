<script setup lang="ts">
import { objectOmit } from '@vueuse/core';
import type AddressInput from '@/components/accounts/blockchain/AddressInput.vue';
import type { AccountAgnosticManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/types/api/errors';

defineProps<{
  loading: boolean;
}>();

const modelValue = defineModel<AccountAgnosticManage>({ required: true });

const address = ref<InstanceType<typeof AddressInput>>();

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const editMode = computed(() => get(modelValue).mode === 'edit');

const tags = computed<string[]>({
  get() {
    const model = get(modelValue);
    return model.data.tags ?? [];
  },
  set(tags: string[]) {
    const model = get(modelValue);
    const tagData = tags.length > 0 ? tags : null;
    set(modelValue, {
      ...model,
      data: {
        ...model.data,
        tags: tagData,
      },
    });
  },
});

const label = computed<string>({
  get() {
    const model = get(modelValue);
    return model.data.label ?? '';
  },
  set(label: string) {
    const model = get(modelValue);
    const labelData = label ? { label } : {};
    set(modelValue, {
      ...model,
      data: {
        ...objectOmit(model.data, ['label']),
        ...labelData,
      },
    });
  },
});

const addresses = computed<string[]>({
  get() {
    const model = get(modelValue);
    return [model.data.address];
  },
  set(addresses: string[]) {
    const model = get(modelValue);
    set(modelValue, {
      ...model,
      data: {
        ...model.data,
        address: addresses.length > 0 ? addresses[0] : '',
      },
    });
  },
});

function validate(): Promise<boolean> {
  assert(isDefined(address));
  return get(address).validate();
}

defineExpose({
  validate,
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <AddressInput
      ref="address"
      v-model:addresses="addresses"
      v-model:error-messages="errors"
      :disabled="loading || editMode"
      :multi="!editMode"
    />
    <AccountDataInput
      v-model:tags="tags"
      v-model:label="label"
      :disabled="loading"
    />
  </div>
</template>
