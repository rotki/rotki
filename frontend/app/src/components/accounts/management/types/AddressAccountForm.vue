<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import { objectOmit } from '@vueuse/core';
import AddressInput from '@/components/accounts/blockchain/AddressInput.vue';
import type { ValidationErrors } from '@/types/api/errors';
import type { Module } from '@/types/modules';
import type { AccountManage } from '@/composables/accounts/blockchain/use-account-manage';

defineProps<{
  loading: boolean;
}>();

const modelValue = defineModel<AccountManage>({ required: true });

const address = ref<InstanceType<typeof AddressInput>>();
const selectedModules = ref<Module[]>([]);

const { isEvm } = useSupportedChains();

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
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
    const labelData = label ? { label } : {};
    if (model.mode === 'edit') {
      set(modelValue, {
        ...model,
        data: {
          ...objectOmit(model.data, ['label']),
          ...labelData,
        },
      });
    }
    else {
      set(modelValue, {
        ...model,
        data: [...model.data.map(item => ({ ...objectOmit(item, ['label']), ...labelData }))],
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
          tags: accountTags.length > 0 ? accountTags : null,
          ...(accountLabel ? { label: accountLabel } : {}),
        })),
      });
    }
  },
});

const allEvmChains = computed<boolean>({
  get() {
    const model = get(modelValue);
    if (model.mode !== 'edit')
      return model.evm ?? false;

    return false;
  },
  set(evm) {
    const model = get(modelValue);
    if (model.mode === 'edit')
      return;

    set(modelValue, { ...model, evm });
  },
});

const showEvmCheck = computed<boolean>(() => {
  const model = get(modelValue);
  return get(isEvm(model.chain)) && model.mode !== 'edit';
});

function onAllEvmChainsUpdate(allChains: boolean) {
  set(allEvmChains, allChains);
}

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
      v-if="modelValue.chain === Blockchain.ETH && !editMode"
      @update:selection="selectedModules = $event"
    />

    <slot
      v-if="showEvmCheck"
      name="selector"
      :disabled="loading"
      :attrs="{ 'modelValue': allEvmChains, 'onUpdate:model-value': onAllEvmChainsUpdate }"
    />

    <div class="flex flex-col gap-4">
      <AddressInput
        ref="address"
        v-model:addresses="addresses"
        v-model:error-messages="errors"
        :disabled="loading || editMode"
        :multi="!editMode"
        :show-wallet-import="showEvmCheck"
      />
      <AccountDataInput
        v-model:tags="tags"
        v-model:label="label"
        :disabled="loading"
      />
    </div>
  </div>
</template>
