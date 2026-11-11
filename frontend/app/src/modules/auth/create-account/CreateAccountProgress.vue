<script lang="ts" setup>
/**
 * The wizard's step indicator, drawn in the space above the heading.
 *
 * @remarks
 * It sits outside the flow so the heading, not the indicator, is what the page anchors. The login
 * page has no indicator and anchors its heading at the same offset, so moving between the two pages
 * keeps the heading in place. It occupies the top padding `UserHost` reserves, and the parent must
 * be positioned.
 */
import type { CreateAccountStep } from '@/modules/auth/create-account/use-create-account-steps';

defineProps<{
  steps: CreateAccountStep[];
  step: number;
  current: CreateAccountStep | undefined;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="absolute bottom-full inset-x-0 flex flex-col gap-2 pb-3"
    data-testid="create-account-progress"
  >
    <template v-if="current">
      <div
        class="flex gap-1.5"
        aria-hidden="true"
      >
        <div
          v-for="(item, index) in steps"
          :key="item.id"
          class="h-1 w-12 rounded-full transition-colors duration-300 motion-reduce:transition-none"
          :class="index < step ? 'bg-rui-primary' : 'bg-rui-grey-300 dark:bg-rui-grey-800'"
        />
      </div>
      <p
        class="text-caption uppercase tracking-wide text-rui-text-secondary"
        data-testid="create-account-step-progress"
      >
        {{ t('create_account.step_progress', { current: step, total: steps.length }) }}
      </p>
    </template>
  </div>
</template>
