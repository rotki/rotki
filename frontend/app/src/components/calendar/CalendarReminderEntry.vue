<script setup lang="ts">
import { helpers, maxValue, minValue, required } from '@vuelidate/validators';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import type { CalendarReminderTemporaryPayload } from '@/types/history/calendar/reminder';

const props = defineProps<{
  value: CalendarReminderTemporaryPayload;
  latest: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', value: CalendarReminderTemporaryPayload): void;
  (e: 'delete'): void;
}>();

const { latest } = toRefs(props);

const vModel = useSimpleVModel(props, emit);

const { t } = useI18n();

enum Unit {
  MINUTES = 'minutes',
  HOURS = 'hours',
  DAYS = 'days',
  WEEKS = 'weeks',
}

interface UnitData {
  key: Unit;
  label: string;
  seconds: number;
};

const unitData: ComputedRef<UnitData[]> = computed(() => ([
  {
    key: Unit.MINUTES,
    label: t('calendar.reminder.units.minutes'),
    seconds: 60,
  },
  {
    key: Unit.HOURS,
    label: t('calendar.reminder.units.hours'),
    seconds: 60 * 60,
  },
  {
    key: Unit.DAYS,
    label: t('calendar.reminder.units.days'),
    seconds: 60 * 60 * 24,
  },
  {
    key: Unit.WEEKS,
    label: t('calendar.reminder.units.weeks'),
    seconds: 60 * 60 * 24 * 7,
  },
]));

const amount: Ref<string> = ref('1');
const unit: Ref<Unit> = ref(Unit.HOURS);

const MAX_ALLOWED = 60 * 60 * 24 * 30; // 30 Days

const selectedUnit: ComputedRef<UnitData | undefined> = computed(() => {
  const selectedUnit = get(unit);
  return get(unitData).find(item => item.key === selectedUnit);
});

const maxAmountAllowed: ComputedRef<number> = computed(() => {
  const data = get(selectedUnit);
  if (!data)
    return 0;

  return Math.floor(MAX_ALLOWED / data.seconds);
});

const rules = {
  amount: {
    required: helpers.withMessage(
      t('calendar.reminder.validation.amount.non_empty'),
      required,
    ),
    max: helpers.withMessage(
      () => t('calendar.reminder.validation.amount.max_value', {
        amount: get(maxAmountAllowed),
        unit: get(selectedUnit)?.label,
      }),
      maxValue(maxAmountAllowed),
    ),
    min: helpers.withMessage(
      () => t('calendar.reminder.validation.amount.min_value'),
      minValue(1),
    ),
  },
  unit: {
    required: helpers.withMessage(
      t('calendar.reminder.validation.unit.non_empty'),
      required,
    ),
  },
};

const v$ = useVuelidate(
  rules,
  {
    amount,
    unit,
  },
  {
    $autoDirty: true,
  },
);

function calculateCurrentSeconds(): number {
  const item = get(unitData).find(item => item.key === get(unit));

  if (item)
    return Number(get(amount)) * item.seconds;

  return 0;
}

function calculateAmountAndUnit(seconds: number) {
  const unitDataVal = get(unitData);

  let unit: Unit = Unit.MINUTES;
  let amount = Math.floor(seconds / 60);

  unitDataVal.reverse().find((item) => {
    const tempAmount = seconds / item.seconds;
    if (tempAmount % 1 === 0) {
      unit = item.key;
      amount = tempAmount;
      return true;
    }

    return false;
  });

  return {
    unit,
    amount,
  };
}

watchImmediate(vModel, (value) => {
  const currentSeconds = calculateCurrentSeconds();
  const seconds = value.secsBefore;

  if (seconds !== currentSeconds) {
    const { unit: tempUnit, amount: tempAmount } = calculateAmountAndUnit(seconds);

    set(unit, tempUnit);
    set(amount, tempAmount.toString());
  }
});

function triggerUpdate() {
  const amountVal = get(amount);
  const unitVal = get(unit);

  if (amountVal && unitVal && !get(v$).$invalid) {
    const currentSeconds = calculateCurrentSeconds();
    set(vModel, {
      ...get(vModel),
      secsBefore: currentSeconds,
    });
  }
}

const amountInputWrapper = ref();
onMounted(() => {
  if (get(latest)) {
    const input = get(amountInputWrapper)?.$el.querySelector('input');
    input?.select();
  }
});
</script>

<template>
  <div class="flex gap-4">
    <AmountInput
      ref="amountInputWrapper"
      v-model="amount"
      label="Amount"
      integer
      variant="outlined"
      :error-messages="toMessages(v$.amount)"
      dense
      @blur="triggerUpdate()"
    />
    <div
      class="w-[10rem]"
    >
      <RuiMenuSelect
        v-model="unit"
        label="Unit"
        :options="unitData"
        variant="outlined"
        full-width
        key-attr="key"
        dense
        :error-messages="toMessages(v$.unit)"
        @input="triggerUpdate()"
      />
    </div>

    <div class="pt-2 text-rui-text-secondary text-sm">
      {{ t('calendar.reminder.before_event') }}
    </div>
    <div>
      <RuiButton
        icon
        color="error"
        variant="text"
        class="!p-2"
        @click="emit('delete')"
      >
        <RuiIcon
          size="20"
          name="delete-bin-line"
        />
      </RuiButton>
    </div>
  </div>
</template>
