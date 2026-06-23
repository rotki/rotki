<script setup lang="ts">
import type { LocationDataSnapshot, LocationDataSnapshotPayload } from '@/modules/dashboard/snapshots';
import { bigNumberify } from '@rotki/common';
import EditLocationDataSnapshotForm from '@/modules/dashboard/edit-snapshot/EditLocationDataSnapshotForm.vue';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { convertFiatToUsd, convertUsdToFiat } from '@/modules/dashboard/snapshots/utils/snapshot-fx';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

type IndexedLocationDataSnapshot = LocationDataSnapshot & { index: number };

/** Whether the dialog is open; exposed so a host drawer can stay stateless. */
const openDialog = defineModel<boolean>('open', { default: false });

const { locations, timestamp } = defineProps<{
  /** Existing location rows (real + total) — used to exclude duplicate names. */
  locations: LocationDataSnapshot[];
  timestamp: number;
}>();

const emit = defineEmits<{
  /** A validated add (index null) or edit (index set) of a location row. */
  submit: [payload: { index: number | null; location: LocationDataSnapshot }];
}>();

const { t } = useI18n({ useScope: 'global' });

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const stateUpdated = ref<boolean>(false);
const submitting = ref<boolean>(false);
const editedIndex = ref<number | null>(null);
const formModel = ref<LocationDataSnapshotPayload | null>(null);
const excludedLocations = ref<string[]>([]);

const form = useTemplateRef<InstanceType<typeof EditLocationDataSnapshotForm>>('form');

// Snapshots are stored in USD; editing in the user's fiat must use the historic
// USD -> fiat rate at the snapshot's timestamp, not today's (#12277).
const { isUsd, loading, rate, rateReady } = useHistoricFiatConversion(() => timestamp);

// Without a historic forex rate the fiat value can't be converted back to USD;
// block the save and point the user at the summary's exchange-rate control.
const rateMissing = computed<boolean>(() => !get(isUsd) && !get(rateReady));
// Only surface the dead-end once the lookup has settled, so it doesn't flash
// while the historic rate is still being fetched.
const showRateMissing = computed<boolean>(() => get(rateMissing) && !get(loading));

function openAdd(): void {
  set(editedIndex, null);
  set(formModel, { location: '', timestamp, usdValue: '' });
  set(excludedLocations, locations.map(item => item.location));
  set(openDialog, true);
}

function openEdit(item: IndexedLocationDataSnapshot): void {
  set(editedIndex, item.index);
  set(formModel, {
    ...item,
    usdValue: get(isUsd) ? item.usdValue.toFixed() : convertUsdToFiat(item.usdValue, get(rate)).toFixed(),
  });
  set(excludedLocations, locations.map(loc => loc.location).filter(name => name !== item.location));
  set(openDialog, true);
}

function close(): void {
  set(openDialog, false);
  set(editedIndex, null);
  set(formModel, null);
  set(excludedLocations, []);
}

async function save(): Promise<void> {
  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return;

  const formData = get(formModel);
  if (!formData)
    return;

  set(submitting, true);

  const usdValue = get(isUsd)
    ? bigNumberify(formData.usdValue)
    : convertFiatToUsd(bigNumberify(formData.usdValue), get(rate));

  set(submitting, false);

  emit('submit', {
    index: get(editedIndex),
    location: { location: formData.location, timestamp, usdValue },
  });

  close();
}

defineExpose({
  openAdd,
  openEdit,
});
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="
      editedIndex !== null
        ? t('dashboard.snapshot.edit.dialog.location_data.edit_title')
        : t('dashboard.snapshot.edit.dialog.location_data.add_title')
    "
    :primary-action="t('common.actions.save')"
    :loading="submitting"
    :action-disabled="rateMissing"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="close()"
  >
    <RuiAlert
      v-if="showRateMissing"
      type="warning"
      class="mb-4"
    >
      {{ t('dashboard.snapshot.detail.fx_override.missing.description', { symbol: currencySymbol }) }}
    </RuiAlert>
    <EditLocationDataSnapshotForm
      v-if="formModel"
      ref="form"
      v-model="formModel"
      v-model:state-updated="stateUpdated"
      :excluded-locations="excludedLocations"
    />
  </BigDialog>
</template>
