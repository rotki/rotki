<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert } from '@rotki/common';
import Eth2Input from '@/modules/accounts/blockchain/Eth2Input.vue';
import { ActivityPart } from '@/modules/task-center/core/types';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

// The validator itself rather than the account state holding it: this form edits one field of that
// state, and taking the whole thing only meant unwrapping it again here.
const validator = defineModel<Eth2Validator>('validator', { required: true });

const errorMessages = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  editMode: boolean;
  loading: boolean;
}>();

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
    :edit-mode="editMode"
    :disabled="loading || taskRunning"
  />
</template>
