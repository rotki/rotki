<template>
  <v-form
    :value="value"
    data-cy="ledger-action-form"
    class="ledger-action-form"
    @input="input"
  >
    <location-selector
      v-model="location"
      class="pt-1"
      required
      outlined
      data-cy="location"
      :rules="locationRules"
      :label="tc('common.location')"
      :error-messages="errorMessages['location']"
      @focus="delete errorMessages['location']"
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
      @focus="delete errorMessages['timestamp']"
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
          :rules="assetRules"
          :error-messages="errorMessages['asset']"
          @focus="delete errorMessages['asset']"
        />
      </v-col>

      <v-col cols="12" md="4">
        <amount-input
          v-model="amount"
          outlined
          :rules="amountRules"
          required
          data-cy="amount"
          :label="tc('common.amount')"
          :error-messages="errorMessages['amount']"
          @focus="delete errorMessages['amount']"
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
          :error-messages="errorMessages['actionType']"
          @focus="delete errorMessages['actionType']"
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
          :error-messages="errorMessages['rate']"
          @focus="delete errorMessages['rate']"
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
          :error-messages="errorMessages['rateAsset']"
          @focus="delete errorMessages['rateAsset']"
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
      @focus="delete errorMessages['link']"
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
      @focus="delete errorMessages['notes']"
    />
  </v-form>
</template>

<script setup lang="ts">
import dayjs from 'dayjs';
import { PropType } from 'vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import { ledgerActionsData } from '@/store/history/consts';
import { LedgerActionEntry } from '@/store/history/types';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { LedgerAction, NewLedgerAction } from '@/types/history/ledger-actions';
import { LedgerActionType } from '@/types/ledger-actions';
import { bigNumberifyFromRef, Zero } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

const props = defineProps({
  value: { required: false, type: Boolean, default: false },
  edit: {
    required: false,
    type: Object as PropType<LedgerAction | null>,
    default: null
  },
  saveData: {
    required: true,
    type: Function as PropType<
      (trade: NewLedgerAction | LedgerActionEntry) => Promise<ActionStatus>
    >
  }
});

const emit = defineEmits<{
  (e: 'input', valid: boolean): void;
}>();

const { edit, saveData } = toRefs(props);

const input = (valid: boolean) => emit('input', valid);

const lastLocation = useLocalStorage(
  'rotki.ledger_action.location',
  TRADE_LOCATION_EXTERNAL
);

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

const errorMessages = ref<{ [field: string]: string[] }>({});

const { t, tc } = useI18n();

const amountRules = [
  (v: string) =>
    !!v || t('ledger_action_form.amount.validation.non_empty').toString()
];
const assetRules = [
  (v: string) =>
    !!v || t('ledger_action_form.asset.validation.non_empty').toString()
];
const locationRules = [
  (v: string) =>
    !!v || t('ledger_action_form.location.validation.non_empty').toString()
];

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
  const ledgerAction = get(edit);
  if (!ledgerAction) {
    reset();
    return;
  }

  set(location, ledgerAction.location);
  set(datetime, convertFromTimestamp(ledgerAction.timestamp, true));
  set(asset, ledgerAction.asset);
  set(amount, ledgerAction.amount.toFixed());
  set(actionType, ledgerAction.actionType.toString());
  set(rate, ledgerAction.rate?.toFixed() ?? '');
  set(rateAsset, ledgerAction.rateAsset ?? '');
  set(link, ledgerAction.link ?? '');
  set(notes, ledgerAction.notes ?? '');
  set(id, ledgerAction.identifier);
};

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

  const save = get(saveData);
  const result = !get(id)
    ? await save(ledgerActionPayload)
    : await save({ ...ledgerActionPayload, identifier: get(id)! });

  if (result.success) {
    reset();
    return true;
  }

  if (result.message) {
    set(
      errorMessages,
      convertKeys(deserializeApiErrorMessage(result.message) ?? {}, true, false)
    );
  }

  return false;
};

watch(edit, () => {
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
