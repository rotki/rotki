<script setup lang="ts">
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import { TaskType } from '@/types/task-type';
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/types/api/errors';

const props = defineProps<{
  modelValue: StakingValidatorManage;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: StakingValidatorManage): void;
}>();

const input = ref<InstanceType<typeof Eth2Input>>();

const validator = useSimplePropVModel(props, 'data', emit);
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

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
    v-model:error-messages="errors"
    :edit-mode="modelValue.mode === 'edit'"
    :disabled="loading || taskRunning"
  />
</template>
