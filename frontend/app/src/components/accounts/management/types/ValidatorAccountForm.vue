<script setup lang="ts">
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/types/api/errors';

const props = defineProps<{
  value: StakingValidatorManage;
  errorMessages: ValidationErrors;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', value: StakingValidatorManage): void;
}>();

const input = ref<InstanceType<typeof Eth2Input>>();

const validator = useSimplePropVModel(props, 'data', emit);

async function validate(): Promise<boolean> {
  assert(isDefined(input));
  return get(input).validate();
}

defineExpose({
  validate,
});
</script>

<template>
  <Eth2Input
    ref="input"
    :validator.sync="validator"
    :disabled="loading || value.mode === 'edit'"
    :error-messages="errorMessages"
  />
</template>
