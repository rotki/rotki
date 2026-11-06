<script setup lang="ts">
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import SimpleRpcNodeManagerForm from '@/modules/settings/general/rpc/simple/SimpleRpcNodeManagerForm.vue';
import { useSettingsWriter } from '@/modules/settings/settings-writer';
import { useSetting } from '@/modules/settings/use-setting';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { setting } = defineProps<{
  setting: 'ksmRpcEndpoint' | 'dotRpcEndpoint' | 'beaconRpcEndpoint' | 'btcMempoolApi';
}>();

const { t } = useI18n({ useScope: 'global' });

const openDialog = ref<boolean>(false);
const submitting = ref<boolean>(false);
const errorMessages = ref<ValidationErrors>({});
const form = useTemplateRef<InstanceType<typeof SimpleRpcNodeManagerForm>>('form');
const stateUpdated = ref(false);
const inputUrl = ref<string>('');
/** Why the last delete failed, until the next one starts; the row stays, so its button is the retry. */
const deleteFailure = ref<string>();

const value = useSetting(setting);
const { write } = useSettingsWriter();

function addNewRpcNode() {
  set(errorMessages, {});
  set(openDialog, true);
  set(inputUrl, '');
}

function edit(item: string) {
  set(errorMessages, {});
  set(openDialog, true);
  set(inputUrl, item);
}

async function save(): Promise<void> {
  if (!get(form)?.validate())
    return;

  const value = get(inputUrl);

  set(submitting, true);

  const result = await write(setting, value);

  set(submitting, false);

  if (result.success) {
    set(openDialog, false);
  }
  else {
    set(errorMessages, { modelValue: result.message ?? '' });
  }
}

const deleteConfirm = computed<RowDeleteQuestion>(() => ({
  message: t('general_settings.simple_node_setting.delete_confirmation.subtitle'),
  title: t('general_settings.simple_node_setting.delete_confirmation.title'),
}));

/** Clears the endpoint, which the row's delete button already confirmed. */
async function deleteNode(): Promise<void> {
  set(deleteFailure, undefined);
  const result = await write(setting, '');
  if (!result.success)
    set(deleteFailure, result.message ?? '');
}

defineExpose({
  addNewRpcNode,
});
</script>

<template>
  <FailureStrip
    v-if="deleteFailure !== undefined"
    class="mb-2"
    :title="t('general_settings.simple_node_setting.delete_error')"
    :failure="deleteFailure"
    data-testid="simple-node-delete-error"
  />
  <RuiTable
    class="bg-white dark:bg-transparent"
    :empty="!value"
  >
    <thead>
      <tr>
        <th>{{ t('evm_rpc_node_manager.node') }}</th>
        <th />
      </tr>
    </thead>
    <tbody>
      <tr v-if="value">
        <td class="py-4">
          <div class="flex gap-3 items-center">
            <RuiTooltip
              v-if="!value.includes('localhost')"
              :options="{ placement: 'top' }"
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
              :options="{ placement: 'top' }"
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
            :delete-confirm="deleteConfirm"
            @edit-click="edit(value)"
            @delete-click="deleteNode()"
          />
        </td>
      </tr>
    </tbody>
    <template #empty>
      <RuiTableEmptyState
        compact
        :label="t('data_table.no_data')"
      >
        <template #description>
          <RuiButton
            color="primary"
            class="mt-2"
            data-testid="add-simple-node"
            @click="addNewRpcNode()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-plus"
                size="16"
              />
            </template>
            {{ t('evm_rpc_node_manager.add_button') }}
          </RuiButton>
        </template>
      </RuiTableEmptyState>
    </template>
  </RuiTable>
  <BigDialog
    :display="openDialog"
    :title="t('evm_rpc_node_manager.add_dialog.title')"
    :action="{ primary: t('common.actions.save') }"
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
      :disabled="submitting"
    />
  </BigDialog>
</template>
