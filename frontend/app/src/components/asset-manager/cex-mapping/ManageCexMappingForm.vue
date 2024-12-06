<script setup lang="ts">
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { objectOmit } from '@vueuse/core';
import { toMessages } from '@/utils/validation';
import { useRefPropVModel } from '@/utils/model';
import { useMessageStore } from '@/store/message';
import { useCexMappingForm } from '@/composables/assets/forms/cex-mapping-form';
import { useAssetCexMappingApi } from '@/composables/api/assets/cex-mapping';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import ExchangeInput from '@/components/inputs/ExchangeInput.vue';
import type { CexMapping } from '@/types/asset';

const props = withDefaults(
  defineProps<{
    editMode?: boolean;
    form?: Partial<CexMapping> | null;
    selectedLocation?: string;
  }>(),
  {
    editMode: false,
    form: null,
    selectedLocation: undefined,
  },
);

const { form, selectedLocation } = toRefs(props);

const emptyMapping: () => CexMapping = () => ({
  asset: '',
  location: get(selectedLocation) || '',
  locationSymbol: '',
});

const formData = ref<CexMapping>(emptyMapping());
const asset = useRefPropVModel(formData, 'asset');
const locationSymbol = useRefPropVModel(formData, 'locationSymbol');
const location = computed<string>({
  get() {
    return get(formData, 'location') ?? '';
  },
  set(value?: string) {
    set(formData, {
      ...objectOmit(get(formData), ['location']),
      location: value ?? null,
    });
  },
});

const forAllExchanges = ref<boolean>(false);

function checkPassedForm() {
  const data = get(form);
  if (data) {
    set(forAllExchanges, !data.location);
    set(formData, data);
  }
  else {
    set(forAllExchanges, false);
    set(formData, emptyMapping());
  }
}

watchImmediate(form, checkPassedForm);

const { t } = useI18n();

const { setSubmitFunc, setValidation } = useCexMappingForm();

const rules = {
  asset: {
    required: helpers.withMessage(t('asset_management.cex_mapping.form.asset_non_empty'), required),
  },
  location: {
    required: helpers.withMessage(
      t('asset_management.cex_mapping.form.location_non_empty'),
      requiredIf(logicNot(forAllExchanges)),
    ),
  },
  locationSymbol: {
    required: helpers.withMessage(
      t('asset_management.cex_mapping.form.location_symbol_non_empty'),
      required,
    ),
  },
};

const v$ = setValidation(
  rules,
  {
    asset,
    location,
    locationSymbol,
  },
  { $autoDirty: true },
);

const { setMessage } = useMessageStore();
const { addCexMapping, editCexMapping } = useAssetCexMappingApi();

async function save(): Promise<boolean> {
  const data = get(formData);
  let success = false;
  const editMode = props.editMode;
  const payload = {
    ...data,
    location: get(forAllExchanges) ? null : data.location,
  };

  try {
    if (editMode)
      success = await editCexMapping(payload);
    else success = await addCexMapping(payload);
  }
  catch (error: any) {
    const obj = { message: error.message };
    setMessage({
      description: editMode
        ? t('asset_management.cex_mapping.add_error', obj)
        : t('asset_management.cex_mapping.edit_error', obj),
    });
  }

  return success;
}

setSubmitFunc(save);
</script>

<template>
  <div class="flex flex-col gap-2">
    <RuiSwitch
      v-model="forAllExchanges"
      :disabled="editMode"
      color="primary"
    >
      {{ t('asset_management.cex_mapping.save_for_all') }}
    </RuiSwitch>
    <ExchangeInput
      v-model="location"
      :label="t('asset_management.cex_mapping.exchange')"
      :disabled="editMode || forAllExchanges"
      clearable
      :error-messages="toMessages(v$.location)"
    />
    <RuiTextField
      v-model="locationSymbol"
      data-cy="locationSymbol"
      variant="outlined"
      color="primary"
      :disabled="editMode"
      clearable
      :label="t('asset_management.cex_mapping.location_symbol')"
      :error-messages="toMessages(v$.locationSymbol)"
    />
    <AssetSelect
      v-model="asset"
      :label="t('asset_management.cex_mapping.recognized_as')"
      outlined
      :error-messages="toMessages(v$.asset)"
    />
  </div>
</template>
