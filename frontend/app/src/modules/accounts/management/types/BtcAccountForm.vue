<script setup lang="ts">
import type { XpubPayload } from '@/modules/accounts/blockchain-accounts';
import type { XpubManage } from '@/modules/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert } from '@rotki/common';
import { omit } from 'es-toolkit';
import BtcAddressInput from '@/modules/accounts/blockchain/BtcAddressInput.vue';
import AccountDataInput from '@/modules/accounts/management/inputs/AccountDataInput.vue';

const modelValue = defineModel<XpubManage>({ required: true });

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  'detected-address': [address: string];
}>();

const input = useTemplateRef<InstanceType<typeof BtcAddressInput>>('input');

const xpub = computed<XpubPayload>({
  get() {
    const model = get(modelValue);
    return model.data.xpub;
  },
  set(xpub: XpubPayload) {
    const model = get(modelValue);
    set(modelValue, {
      ...model,
      data: {
        ...model.data,
        xpub,
      },
    });
  },
});

const tags = computed<string[]>({
  get() {
    return get(modelValue).data.tags ?? [];
  },
  set(tags: string[]) {
    const model = get(modelValue);
    set(modelValue, {
      ...model,
      data: {
        ...model.data,
        tags: tags.length > 0 ? tags : null,
      },
    });
  },
});

const label = computed<string>({
  get() {
    return get(modelValue).data.label ?? '';
  },
  set(label: string) {
    const model = get(modelValue);
    const labelData = label ? { label } : {};
    set(modelValue, {
      ...model,
      data: {
        ...omit(model.data, ['label']),
        ...labelData,
      },
    });
  },
});

function validate(): Promise<boolean> {
  assert(isDefined(input));
  return get(input).validate();
}

defineExpose({
  validate,
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <BtcAddressInput
      ref="input"
      v-model:xpub="xpub"
      v-model:error-messages="errors"
      :disabled="loading || modelValue.mode === 'edit'"
      :blockchain="modelValue.chain"
      @detected-address="emit('detected-address', $event)"
    />
    <AccountDataInput
      v-model:tags="tags"
      v-model:label="label"
      :disabled="loading"
    />
  </div>
</template>
