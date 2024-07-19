<script setup lang="ts">
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import { TaskType } from '@/types/task-type';
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/types/api/errors';
import type { ComponentExposed } from 'vue-component-type-helpers';

defineProps<{
  loading: boolean;
}>();

const modelValue = defineModel<StakingValidatorManage>({ required: true });
const errorMessages = defineModel<ValidationErrors>('errorMessages', { required: true });
const validator = useRefPropVModel(modelValue, 'data');

const input = ref<ComponentExposed<typeof Eth2Input>>();

function validate(): Promise<boolean> {
  assert(isDefined(input));
  return get(input).validate();
}

defineExpose({
  validate,
});

const { isTaskRunning } = useTaskStore();
const taskRunning = isTaskRunning(TaskType.ADD_ETH2_VALIDATOR);
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
