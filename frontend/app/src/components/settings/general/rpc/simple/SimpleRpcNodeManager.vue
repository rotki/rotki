<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import SimpleTable from '@/components/common/SimpleTable.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RowActions from '@/components/helper/RowActions.vue';
import SimpleRpcNodeManagerForm from '@/components/settings/general/rpc/simple/SimpleRpcNodeManagerForm.vue';
import { SettingLocation, useSettings } from '@/composables/settings';
import { useConfirmStore } from '@/store/confirm';
import { useGeneralSettingsStore } from '@/store/settings/general';

const props = defineProps<{
  setting: 'ksmRpcEndpoint' | 'dotRpcEndpoint' | 'beaconRpcEndpoint' | 'btcMempoolApi';
}>();

const { t } = useI18n({ useScope: 'global' });

const openDialog = ref<boolean>(false);
const submitting = ref<boolean>(false);
const errorMessages = ref<ValidationErrors>({});
const form = ref<InstanceType<typeof SimpleRpcNodeManagerForm>>();
const stateUpdated = ref(false);
const inputUrl = ref<string>('');

const generalSettings = storeToRefs(useGeneralSettingsStore());
const { updateSetting } = useSettings();

const value = computed(() => get(generalSettings[props.setting]));

function addNewRpcNode() {
  set(openDialog, true);
  set(inputUrl, '');
}

function edit(item: string) {
  set(openDialog, true);
  set(inputUrl, item);
}

async function save(force: boolean = false) {
  if (!(await get(form)?.validate()) && !force)
    return;

  const value = get(inputUrl);

  set(submitting, true);

  const result = await updateSetting(props.setting, value, SettingLocation.GENERAL, {
    error: '',
    success: '',
  });

  set(submitting, false);

  if ('success' in result) {
    set(openDialog, false);
  }
  else {
    set(errorMessages, { modelValue: result.error });
  }
}

const { show } = useConfirmStore();

async function deleteNode() {
  set(inputUrl, '');
  await save(true);
}

function showDeleteConfirmation() {
  show(
    {
      message: t('general_settings.simple_node_setting.delete_confirmation.subtitle'),
      title: t('general_settings.simple_node_setting.delete_confirmation.title'),
    },
    () => deleteNode(),
  );
}

defineExpose({
  addNewRpcNode,
});
</script>

<template>
  <SimpleTable class="bg-white dark:bg-transparent">
    <thead>
      <tr>
        <th>{{ t('evm_rpc_node_manager.node') }}</th>
        <th />
      </tr>
    </thead>
    <tbody>
      <tr v-if="value">
        <td class="!py-4">
          <div class="flex gap-3 items-center">
            <RuiTooltip
              v-if="!value.includes('localhost')"
              :popper="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiIcon
                  name="lu-earth"
                  class="text-rui-text-secondary"
                />
              </template>
              <span>{{ t('evm_rpc_node_manager.public_node') }}</span>
            </RuiTooltip>
            <RuiTooltip
              v-else
              :popper="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiIcon
                  name="lu-user"
                  class="text-rui-text-secondary"
                />
              </template>
              <span>{{ t('evm_rpc_node_manager.private_node') }}</span>
            </RuiTooltip>
            <div>
              {{ value }}
            </div>
          </div>
        </td>
        <td class="w-20">
          <RowActions
            :delete-tooltip="t('evm_rpc_node_manager.delete_tooltip')"
            :edit-tooltip="t('evm_rpc_node_manager.edit_tooltip')"
            @edit-click="edit(value)"
            @delete-click="showDeleteConfirmation()"
          />
        </td>
      </tr>
      <tr v-else>
        <td
          colspan="2"
          class="!py-4 text-rui-text-secondary text-center w-full"
        >
          {{ t('data_table.no_data') }}
        </td>
      </tr>
    </tbody>
  </SimpleTable>
  <BigDialog
    :display="openDialog"
    :title="t('evm_rpc_node_manager.add_dialog.title')"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :prompt-on-close="stateUpdated"
    :loading="submitting"
    @confirm="save()"
    @cancel="openDialog = false"
  >
    <SimpleRpcNodeManagerForm
      ref="form"
      v-model="inputUrl"
      v-model:state-updated="stateUpdated"
      v-model:error-messages="errorMessages"
    />
  </BigDialog>
</template>
