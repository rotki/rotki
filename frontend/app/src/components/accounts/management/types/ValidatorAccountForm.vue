<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/types/api/errors';
import { assert } from '@rotki/common';
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { useRefPropVModel } from '@/utils/model';

const modelValue = defineModel<StakingValidatorManage>({ required: true });

const errorMessages = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
}>();

const validator = useRefPropVModel(modelValue, 'data');

const input = ref<ComponentExposed<typeof Eth2Input>>();

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
