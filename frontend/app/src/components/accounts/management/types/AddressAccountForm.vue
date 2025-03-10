<script setup lang="ts">
import type { AccountManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/types/api/errors';
import type { Module } from '@/types/modules';
import AddressInput from '@/components/accounts/blockchain/AddressInput.vue';
import AccountDataInput from '@/components/accounts/management/inputs/AccountDataInput.vue';
import ModuleActivator from '@/components/accounts/ModuleActivator.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { assert, Blockchain } from '@rotki/common';

const modelValue = defineModel<AccountManage>({ required: true });

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
}>();

const address = ref<InstanceType<typeof AddressInput>>();
const selectedModules = ref<Module[]>([]);

const { isEvm } = useSupportedChains();

const editMode = computed(() => get(modelValue).mode === 'edit');

const tags = computed<string[]>({
  get() {
    const model = get(modelValue);
    return (model.mode === 'edit' ? model.data.tags : model.data.length > 0 ? model.data[0].tags : null) ?? [];
  },
  set(tags: string[]) {
    const model = get(modelValue);
    const tagData = tags.length > 0 ? tags : null;
    if (model.mode === 'edit') {
      set(modelValue, {
        ...model,
        data: {
          ...model.data,
          tags: tagData,
        },
      });
    }
    else {
      set(modelValue, {
        ...model,
        data: [...model.data.map(item => ({ ...item, tags: tagData }))],
      });
    }
  },
});

const label = computed<string>({
  get() {
    const model = get(modelValue);
    return (model.mode === 'edit' ? model.data.label : model.data.length > 0 ? model.data[0].label : null) ?? '';
  },
  set(label: string) {
    const model = get(modelValue);
    if (model.mode === 'edit') {
      set(modelValue, {
        ...model,
        data: {
          ...model.data,
          label,
        },
      });
    }
    else {
      set(modelValue, {
        ...model,
        data: [...model.data.map(item => ({ ...item, label }))],
      });
    }
  },
});

const addresses = computed<string[]>({
  get() {
    const model = get(modelValue);
    return model.mode === 'edit' ? [model.data.address] : model.data.map(({ address }) => address);
  },
  set(addresses: string[]) {
    const model = get(modelValue);
    if (model.mode === 'edit') {
      set(modelValue, {
        ...model,
        data: {
          ...model.data,
          address: addresses.length > 0 ? addresses[0] : '',
        },
      });
    }
    else {
      const accountTags = get(tags);
      const accountLabel = get(label);

      set(modelValue, {
        ...model,
        data: addresses.map(address => ({
          address,
          label: accountLabel,
          tags: accountTags.length > 0 ? accountTags : null,
        })),
      });
    }
  },
});

const showWalletImport = computed<boolean>(() => {
  const model = get(modelValue);
  return get(isEvm(model.chain)) || model.chain === 'evm';
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
  <div class="flex flex-col gap-6">
    <ModuleActivator
      v-if="[Blockchain.ETH, 'evm'].includes(modelValue.chain) && !editMode"
      @update:selection="selectedModules = $event"
    />

    <div class="flex flex-col gap-4">
      <AddressInput
        ref="address"
        v-model:addresses="addresses"
        v-model:error-messages="errors"
        :disabled="loading || editMode"
        :multi="!editMode"
        :show-wallet-import="showWalletImport"
      />
      <AccountDataInput
        v-model:tags="tags"
        v-model:label="label"
        :disabled="loading"
      />
    </div>
  </div>
</template>
