import type { Ref } from 'vue';

/**
 * Reports a wizard step's validity to the wizard, starting immediately.
 *
 * @remarks
 * Immediacy is the point: a step that only reported on change would leave `valid` at whatever the
 * wizard defaulted it to, and Continue would gate on that stale value until the user touched a
 * field.
 *
 * @param parses - whether the step's own form currently parses
 * @param valid - the wizard's model for this step, which this writes to
 */
export function syncStepValidity(parses: Ref<boolean>, valid: Ref<boolean>): void {
  syncRefs(parses, valid);
}
