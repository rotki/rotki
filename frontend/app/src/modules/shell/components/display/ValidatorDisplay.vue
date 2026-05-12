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
    :class="{
      flex: horizontal,
      blur: !shouldShowAmount,
    }"
  >
    <div class="font-medium text-truncate text-rui-text">
      {{ truncateAddress(scrambleAddress(validator.publicKey), length) }}
    </div>
    <div>
      <span
        v-if="horizontal"
        class="px-1"
      >
        -
      </span>
      <span
        v-else
        class="text-caption"
      >
        {{ t('common.validator_index') }}:
      </span>
      {{ scrambleIdentifier(validator.index) }}
    </div>
  </div>
</template>
