<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/modules/api/types/errors';
import { assert } from '@rotki/common';
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import { useRefPropVModel } from '@/modules/common/validation/model';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';

const modelValue = defineModel<StakingValidatorManage>({ required: true });

const errorMessages = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
}>();

const validator = useRefPropVModel(modelValue, 'data');

const input = useTemplateRef<ComponentExposed<typeof Eth2Input>>('input');

function validate(): Promise<boolean> {
  assert(isDefined(input));
  return get(input).validate();
}

const { useIsTaskRunning } = useTaskStore();
const taskRunning = useIsTaskRunning(TaskType.ADD_ETH2_VALIDATOR);

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
