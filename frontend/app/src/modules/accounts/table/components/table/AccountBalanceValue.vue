<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/amount-display/components';

interface Props {
  includedValue: BigNumber | undefined;
  loading: boolean;
  value: BigNumber;
}

defineProps<Props>();
</script>

<template>
  <div class="flex flex-col items-end justify-end">
    <div
      v-if="includedValue && !loading"
      class="text-xs"
    >
      <FiatDisplay
        v-if="includedValue"
        :value="includedValue"
      />
      /
    </div>
    <FiatDisplay
      :value="value"
      :loading="loading"
      data-cy="usd-value"
      class="font-medium"
    />
  </div>
</template>
