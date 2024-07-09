<script setup lang="ts">
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import { TaskType } from '@/types/task-type';
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/types/api/errors';

const props = defineProps<{
  value: StakingValidatorManage;
  errorMessages: ValidationErrors;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', value: StakingValidatorManage): void;
  (e: 'update:error-messages', value: ValidationErrors): void;
}>();

const input = ref<InstanceType<typeof Eth2Input>>();

const validator = useSimplePropVModel(props, 'data', emit);
const errors = useKebabVModel(props, 'errorMessages', emit);

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
    :validator.sync="validator"
    :edit-mode="value.mode === 'edit'"
    :disabled="loading || taskRunning"
    :error-messages.sync="errors"
  />
</template>
