<script setup lang="ts">
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useScramble } from '@/modules/settings/use-scramble';

interface ValidatorEntry {
  readonly publicKey: string;
  readonly index: number;
}

const { horizontal = false, validator } = defineProps<{
  validator: ValidatorEntry;
  horizontal?: boolean;
}>();

const HORIZONTAL_TRUNCATE_LENGTH = 4;
const STACKED_TRUNCATE_LENGTH = 10;

const { t } = useI18n({ useScope: 'global' });

const length = computed<number>(() => (horizontal ? HORIZONTAL_TRUNCATE_LENGTH : STACKED_TRUNCATE_LENGTH));

const { scrambleAddress, scrambleIdentifier, shouldShowAmount } = useScramble();
</script>

<template>
  <div
    class="text-truncate"
    :class="[
      horizontal ? 'flex items-baseline gap-1' : 'flex flex-col leading-[1.25em]',
      { blur: !shouldShowAmount },
    ]"
  >
    <div class="font-medium text-truncate text-sm text-rui-text">
      {{ truncateAddress(scrambleAddress(validator.publicKey), length) }}
    </div>
    <div class="text-rui-text-secondary text-caption text-truncate">
      <span v-if="horizontal">-</span>
      <span v-else>{{ t('common.validator_index') }}:</span>
      {{ scrambleIdentifier(validator.index) }}
    </div>
  </div>
</template>
