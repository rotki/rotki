<script setup lang="ts">
import type { BalanceSnapshot, LocationDataSnapshot } from '@/modules/dashboard/snapshots';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/modules/core/common/validation/validation';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import { type TotalSuggestionKey, useSnapshotTotalInput } from '@/modules/dashboard/snapshots/composables/use-snapshot-total-input';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const modelValue = defineModel<LocationDataSnapshot[]>({ required: true });

const { timestamp, balancesSnapshot } = defineProps<{
  timestamp: number;
  balancesSnapshot: BalanceSnapshot[];
}>();

const emit = defineEmits<{
  'update:step': [step: number];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  applyTotal,
  fetchingRate,
  nftsExcludedTotal,
  rateReady,
  setTotal,
  suggestions,
  total,
} = useSnapshotTotalInput({
  balancesSnapshot: () => balancesSnapshot,
  modelValue,
  timestamp: () => timestamp,
});

const rules = {
  total: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.total.rules.total'), required),
  },
};

const v$ = useVuelidate(
  rules,
  { total },
  { $autoDirty: true },
);

const suggestionsLabel = computed<Record<TotalSuggestionKey, string>>(() => ({
  asset: t('dashboard.snapshot.edit.dialog.total.use_calculated_asset', {
    length: balancesSnapshot.length,
  }),
  location: t('dashboard.snapshot.edit.dialog.total.use_calculated_location', {
    length: get(modelValue).length,
  }),
  total: t('dashboard.snapshot.edit.dialog.total.use_calculated_total'),
}));

function updateStep(step: number): void {
  emit('update:step', step);
}

async function save(): Promise<void> {
  if (!(await get(v$).$validate()))
    return;

  applyTotal();
}
</script>

<template>
  <div>
    <div class="py-10 mx-auto max-w-[20rem]">
      <div class="text-h6 mb-4 text-center">
        {{ t('common.total') }}
      </div>
      <div class="mb-4">
        <AmountInput
          v-model="total"
          variant="outlined"
          :error-messages="toMessages(v$.total)"
          :disabled="fetchingRate || !rateReady"
        >
          <template
            v-if="fetchingRate"
            #append
          >
            <RuiProgress
              circular
              thickness="2"
              variant="indeterminate"
              color="primary"
              size="16"
            />
          </template>
        </AmountInput>

        <div class="text-rui-text-secondary text-caption">
          <i18n-t
            scope="global"
            keypath="dashboard.snapshot.edit.dialog.total.warning"
          >
            <template #amount>
              <SnapshotFiatDisplay
                :value="nftsExcludedTotal"
                :timestamp="timestamp"
              />
            </template>
          </i18n-t>
        </div>
      </div>
      <div>
        <div
          v-for="(number, key) in suggestions"
          :key="key"
        >
          <RuiButton
            color="primary"
            class="mb-4 w-full"
            :disabled="!rateReady"
            @click="setTotal(number)"
          >
            <div class="flex flex-col items-center">
              <span>
                {{ suggestionsLabel[key] }}
              </span>
              <SnapshotFiatDisplay
                v-if="number"
                :value="number"
                :timestamp="timestamp"
                class="text-2xl"
              />
            </div>
          </RuiButton>

          <div
            v-if="key === 'location'"
            class="text-rui-text-secondary text-caption"
          >
            {{ t('dashboard.snapshot.edit.dialog.total.hint') }}
          </div>
        </div>
      </div>
    </div>

    <div class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex justify-end p-2 gap-2">
      <RuiButton
        variant="text"
        data-testid="edit-snapshot-prev"
        @click="updateStep(2)"
      >
        <template #prepend>
          <RuiIcon name="lu-arrow-left" />
        </template>
        {{ t('common.actions.back') }}
      </RuiButton>
      <RuiButton
        color="primary"
        data-testid="edit-snapshot-complete"
        @click="save()"
      >
        {{ t('common.actions.finish') }}
        <template #append>
          <RuiIcon name="lu-arrow-right" />
        </template>
      </RuiButton>
    </div>
  </div>
</template>
