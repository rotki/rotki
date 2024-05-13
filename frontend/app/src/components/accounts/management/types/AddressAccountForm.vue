<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { objectOmit } from '@vueuse/core';
import AddressInput from '@/components/accounts/blockchain/AddressInput.vue';
import type { ValidationErrors } from '@/types/api/errors';
import type { Module } from '@/types/modules';
import type { AccountManage } from '@/composables/accounts/blockchain/use-account-manage';

const props = defineProps<{
  value: AccountManage;
  loading: boolean;
  errorMessages: ValidationErrors;
}>();

const emit = defineEmits<{
  (e: 'input', value: AccountManage): void;
  (e: 'update:error-messages', value: ValidationErrors): void;
}>();

const { value: modelValue } = toRefs(props);

const allEvmChains = ref(true);
const address = ref<InstanceType<typeof AddressInput>>();
const selectedModules = ref<Module[]>([]);

const { isEvm } = useSupportedChains();

const errors = useKebabVModel(props, 'errorMessages', emit);
const editMode = computed(() => props.value.mode === 'edit');

function updateVModel(value: AccountManage): void {
  emit('input', value);
}

const tags = computed<string[]>({
  get() {
    const model = get(modelValue);
    return (model.mode === 'edit' ? model.data.tags : model.data.length > 0 ? model.data[0].tags : null) ?? [];
  },
  set(tags: string[]) {
    const model = get(modelValue);
    const tagData = tags.length > 0 ? tags : null;
    if (model.mode === 'edit') {
      updateVModel({
        ...model,
        data: {
          ...model.data,
          tags: tagData,
        },
      });
    }
    else {
      updateVModel({
        ...model,
        data: [...model.data.map(item => ({ ...item, tags: tagData }))],
      });
    }
  },
});

const label = computed<string>({
  get() {
    const model = get(modelValue);
    return (model.mode === 'edit' ? model.data.label : (model.data.length > 0 ? model.data[0].label : null)) ?? '';
  },
  set(label: string) {
    const model = get(modelValue);
    const labelData = label ? { label } : {};
    if (model.mode === 'edit') {
      updateVModel({
        ...model,
        data: {
          ...objectOmit(model.data, ['label']),
          ...labelData,
        },
      });
    }
    else {
      updateVModel({
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
      updateVModel({
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

      updateVModel({
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

const showEvmCheck = computed<boolean>(() => {
  const model = get(modelValue);
  return get(isEvm(model.chain)) && model.mode !== 'edit';
});

function onAllEvmChainsUpdate(allChains: boolean) {
  return set(allEvmChains, allChains);
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
      v-if="value.chain === Blockchain.ETH && !editMode"
      @update:selection="selectedModules = $event"
    />

    <slot
      v-if="showEvmCheck"
      name="selector"
      :disabled="loading"
      :attrs="{ value: allEvmChains }"
      :on="{ input: onAllEvmChainsUpdate }"
    />

    <div class="flex flex-col gap-4">
      <AddressInput
        ref="address"
        :addresses.sync="addresses"
        :error-messages.sync="errors"
        :disabled="loading || editMode"
        :multi="!editMode"
      />
      <AccountDataInput
        :tags.sync="tags"
        :label.sync="label"
        :disabled="loading"
      />
    </div>
  </div>
</template>
