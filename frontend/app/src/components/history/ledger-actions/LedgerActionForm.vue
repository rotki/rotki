<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { type Writeable } from '@/types';
import {
  type LedgerAction,
  type NewLedgerAction
} from '@/types/history/ledger-action/ledger-actions';
import { LedgerActionType } from '@/types/history/ledger-action/ledger-actions-type';
import { Zero, bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation-errors';

const props = withDefaults(
  defineProps<{
    value?: boolean;
    edit?: boolean;
    formData?: Partial<LedgerAction> | null;
  }>(),
  {
    value: false,
    edit: false,
    formData: null
  }
);

const emit = defineEmits<{
  (e: 'input', valid: boolean): void;
}>();

const { edit, formData } = toRefs(props);

const input = (valid: boolean) => emit('input', valid);

const lastLocation = useLocalStorage(
  'rotki.ledger_action.location',
  TRADE_LOCATION_EXTERNAL
);

const { ledgerActionsData } = useLedgerActionData();

const id = ref<number | null>(null);
const location = ref<string>('');
const datetime = ref<string>('');
const asset = ref<string>('');
const amount = ref<string>('');
const actionType = ref<string>('');
const rate = ref<string>('');
const rateAsset = ref<string>('');
const link = ref<string>('');
const notes = ref<string>('');

const errorMessages = ref<Record<string, string[]>>({});

const { t, tc } = useI18n();

const rules = {
  amount: {
    required: helpers.withMessage(
      t('ledger_action_form.amount.validation.non_empty').toString(),
      required
    )
  },
  asset: {
    required: helpers.withMessage(
      t('ledger_action_form.asset.validation.non_empty').toString(),
      required
    )
  },
  location: {
    required: helpers.withMessage(
      t('ledger_action_form.location.validation.non_empty').toString(),
      required
    )
  },
  actionType: {
    required: helpers.withMessage(
      t('ledger_action_form.type.validation.non_empty').toString(),
      required
    )
  },
  rate: {
    required: helpers.withMessage(
      t('ledger_action_form.rate.validation.non_empty').toString(),
      requiredIf(refIsTruthy(rateAsset))
    )
  },
  rateAsset: {
    required: helpers.withMessage(
      t('ledger_action_form.rate_asset.validation.non_empty').toString(),
      requiredIf(refIsTruthy(rate))
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    amount,
    asset,
    location,
    actionType,
    rate,
    rateAsset
  },
  { $autoDirty: true, $externalResults: errorMessages }
);

watch(v$, ({ $invalid }) => {
  input(!$invalid);
});

const reset = () => {
  set(id, null);
  set(location, get(lastLocation));
  set(datetime, convertFromTimestamp(dayjs().unix(), true));
  set(asset, '');
  set(amount, '0');
  set(actionType, LedgerActionType.ACTION_INCOME);
  set(rate, '');
  set(rateAsset, '');
  set(link, '');
  set(notes, '');
  set(errorMessages, {});
};

const setEditMode = () => {
  const ledgerAction = get(formData);
  if (!ledgerAction) {
    reset();
    return;
  }

  set(location, ledgerAction.location);
  if (ledgerAction.timestamp) {
    set(datetime, convertFromTimestamp(ledgerAction.timestamp, true));
  } else {
    set(datetime, convertFromTimestamp(dayjs().unix(), true));
  }
  set(asset, ledgerAction.asset);
  if (ledgerAction.amount) {
    set(amount, ledgerAction.amount.toFixed());
  } else {
    set(amount, '0');
  }
  if (ledgerAction.actionType) {
    set(actionType, ledgerAction.actionType.toString());
  } else {
    set(actionType, LedgerActionType.ACTION_INCOME);
  }
  set(rate, ledgerAction.rate?.toFixed() ?? '');
  set(rateAsset, ledgerAction.rateAsset ?? '');
  set(link, ledgerAction.link ?? '');
  set(notes, ledgerAction.notes ?? '');
  set(id, ledgerAction.identifier);
};

const { setMessage } = useMessageStore();

const { addLedgerAction, editLedgerAction } = useLedgerActions();

const save = async (): Promise<boolean> => {
  const numericAmount = get(bigNumberifyFromRef(amount));
  const numericRate = get(bigNumberifyFromRef(rate));

  const ledgerActionPayload: Writeable<NewLedgerAction> = {
    location: get(location),
    timestamp: convertToTimestamp(get(datetime)),
    asset: get(asset),
    amount: numericAmount.isNaN() ? Zero : numericAmount,
    actionType: get(actionType) as LedgerActionType,
    rate: numericRate.isNaN() || numericRate.isZero() ? undefined : numericRate,
    rateAsset: get(rateAsset) ? get(rateAsset) : undefined,
    link: get(link) ? get(link) : undefined,
    notes: get(notes) ? get(notes) : undefined
  };

  const idVal = get(id);

  const result = !idVal
    ? await addLedgerAction(ledgerActionPayload)
    : await editLedgerAction({ ...ledgerActionPayload, identifier: idVal });

  if (result.success) {
    reset();
    return true;
  }

  if (result.message) {
    if (typeof result.message === 'string') {
      setMessage({
        description: result.message
      });
    } else {
      set(errorMessages, result.message);
      await get(v$).$validate();
    }
  }

  return false;
};

watch([edit, formData], () => {
  setEditMode();
});

watch(location, (location: string) => {
  if (location) {
    set(lastLocation, location);
  }
});

onMounted(() => {
  setEditMode();
});

defineExpose({
  reset,
  save
});
</script>

<template>
  <v-form
    :value="value"
    data-cy="ledger-action-form"
    class="ledger-action-form"
  >
    <location-selector
      v-model="location"
      class="pt-1"
      required
      outlined
      data-cy="location"
      :error-messages="toMessages(v$.location)"
      :label="tc('common.location')"
      @blur="v$.location.$touch()"
    />

    <date-time-picker
      v-model="datetime"
      outlined
      :label="tc('ledger_action_form.date.label')"
      persistent-hint
      required
      seconds
      limit-now
      data-cy="datetime"
      :hint="tc('ledger_action_form.date.hint')"
      :error-messages="errorMessages['timestamp']"
    />

    <v-row
      align="center"
      :class="
        $vuetify.breakpoint.mdAndUp
          ? 'ledger-action-form__amount-wrapper'
          : null
      "
    >
      <v-col cols="12" md="4">
        <asset-select
          v-model="asset"
          outlined
          required
          data-cy="asset"
          :error-messages="toMessages(v$.asset)"
          @blur="v$.asset.$touch()"
        />
      </v-col>

      <v-col cols="12" md="4">
        <amount-input
          v-model="amount"
          outlined
          :error-messages="toMessages(v$.amount)"
          required
          data-cy="amount"
          :label="tc('common.amount')"
          @blur="v$.amount.$touch()"
        />
      </v-col>

      <v-col cols="12" md="4">
        <v-select
          v-model="actionType"
          outlined
          :label="tc('common.type')"
          :items="ledgerActionsData"
          item-value="identifier"
          item-text="label"
          required
          data-cy="action-type"
          :error-messages="toMessages(v$.actionType)"
          @blur="v$.actionType.$touch()"
        />
      </v-col>
    </v-row>

    <v-divider class="mb-6 mt-2" />

    <v-row
      :class="
        $vuetify.breakpoint.mdAndUp ? 'ledger-action-form__rate-wrapper' : null
      "
    >
      <v-col cols="12" md="8">
        <amount-input
          v-model="rate"
          outlined
          persistent-hint
          data-cy="rate"
          :hint="tc('ledger_action_form.rate.hint')"
          :label="tc('ledger_action_form.rate.label')"
          :error-messages="toMessages(v$.rate)"
          @blur="v$.rate.$touch()"
        />
      </v-col>
      <v-col cols="12" md="4">
        <asset-select
          v-model="rateAsset"
          outlined
          :label="tc('ledger_action_form.rate_asset.label')"
          :hint="tc('ledger_action_form.rate_asset.hint')"
          persistent-hint
          data-cy="rate-asset"
          :error-messages="toMessages(v$.rateAsset)"
          @blur="v$.rateAsset.$touch()"
        />
      </v-col>
    </v-row>

    <v-text-field
      v-model="link"
      outlined
      prepend-inner-icon="mdi-link"
      persistent-hint
      data-cy="link"
      :label="tc('ledger_action_form.link.label')"
      :hint="tc('ledger_action_form.link.hint')"
      :error-messages="errorMessages['link']"
    />

    <v-textarea
      v-model="notes"
      prepend-inner-icon="mdi-text-box-outline"
      persistent-hint
      outlined
      data-cy="notes"
      :label="tc('ledger_action_form.notes.label')"
      :hint="tc('ledger_action_form.notes.hint')"
      :error-messages="errorMessages['notes']"
    />
  </v-form>
</template>
