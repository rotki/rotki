<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert } from '@rotki/common';
import Eth2Input from '@/modules/accounts/blockchain/Eth2Input.vue';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import { ActivityPart } from '@/modules/task-center/core/types';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

const modelValue = defineModel<StakingValidatorManage>({ required: true });

const errorMessages = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
}>();

const validator = useRefPropVModel(modelValue, 'data');

const input = useTemplateRef<ComponentExposed<typeof Eth2Input>>('input');

/** The input validates synchronously now; the account form still awaits every child alike. */
async function validate(): Promise<boolean> {
  assert(isDefined(input));
  return get(input).validate();
}

const { useIsActivePrefix } = useTaskCenter();
const taskRunning = useIsActivePrefix(ActivityKind.STAKING, ActivityPart.ADD);

defineExpose({
  validate,
});
</script>

<template>
  <Eth2Input
    ref="input"
    v-model:validator="validator"
    v-model:error-messages="errorMessages"
    :edit-mode="modelValue.mode === 'edit'"
    :disabled="loading || taskRunning"
  />
</template>
