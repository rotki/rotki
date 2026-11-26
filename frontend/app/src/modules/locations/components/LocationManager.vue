<script setup lang="ts">
import type { LocationFormData } from '@/modules/locations/location-form';
import { RuiButton, RuiDataTable, RuiIcon, RuiSwitch, RuiTab, RuiTabs } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import LocationAliasesCard from '@/modules/locations/components/LocationAliasesCard.vue';
import LocationFormDialog from '@/modules/locations/components/LocationFormDialog.vue';
import LocationTreeFilter from '@/modules/locations/components/LocationTreeFilter.vue';
import LocationTreeRowActions from '@/modules/locations/components/LocationTreeRowActions.vue';
import LocationTreeRowName from '@/modules/locations/components/LocationTreeRowName.vue';
import LocationUsageNotice from '@/modules/locations/components/LocationUsageNotice.vue';
import { useLocationManagerTree } from '@/modules/locations/use-location-manager-tree';
import { ROOT_LOCATION, useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

type ManagerTab = 'locations' | 'aliases';

const formData = ref<LocationFormData>();
const addingAlias = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();
const router = useRouter();

const treeStore = useLocationTreeStore();
const {
  actionFailure,
  bringIntoView,
  cols,
  confirmDeletion,
  deleting,
  empty,
  modelBlockedDeletion: blockedDeletion,
  modelPendingDeletion: pendingDeletion,
  modelSearch: search,
  modelShowArchived: showArchived,
  requestDeletion,
  rowClass,
  rows,
  setArchived,
  toggle,
  wholeTree,
} = useLocationManagerTree();

/** The open tab, kept in the url so a link can open the aliases directly. */
const tab = computed<ManagerTab>({
  get: () => (get(route).query.tab === 'aliases' ? 'aliases' : 'locations'),
  set: (value) => {
    startPromise(router.replace({ query: { ...get(route).query, tab: value === 'aliases' ? value : undefined } }));
  },
});

function addBelow(parentIdentifier: string, name?: string): void {
  set(formData, { mode: 'add', name, parentIdentifier });
}

/** A quick-add link adds to the tab it names, which clearing the link from the url would otherwise lose. */
const { consumeAddQuery } = useAddQuery((query) => {
  if (query.tab !== 'aliases')
    return addBelow(ROOT_LOCATION);
  set(tab, 'aliases');
  set(addingAlias, true);
});

onMounted(async () => {
  await consumeAddQuery();
});
</script>

<template>
  <TablePageLayout :title="[t('location_manager.title')]">
    <template #buttons>
      <RuiButton
        v-if="tab === 'locations'"
        color="primary"
        size="lg"
        data-testid="location-manager-add"
        @click="addBelow(ROOT_LOCATION)"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('location_manager.actions.add') }}
      </RuiButton>
      <RuiButton
        v-else
        color="primary"
        size="lg"
        data-testid="location-manager-add"
        @click="addingAlias = true"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('location_manager.aliases.add') }}
      </RuiButton>
    </template>

    <template #tabs>
      <RuiTabs
        v-model="tab"
        color="primary"
        variant="segmented"
        data-testid="location-manager-tabs"
      >
        <RuiTab value="locations">
          {{ t('location_manager.tabs.locations') }}
        </RuiTab>
        <RuiTab value="aliases">
          {{ t('location_manager.tabs.aliases') }}
        </RuiTab>
      </RuiTabs>
    </template>

    <TableFrame v-if="tab === 'locations'">
      <template #toolbar>
        <LocationTreeFilter
          v-model:name="search"
          class="flex-1 min-w-64"
        />
        <RuiSwitch
          v-model="showArchived"
          color="primary"
          hide-details
          :label="t('location_manager.show_archived')"
          data-testid="location-manager-show-archived"
        />
      </template>
      <RuiDataTable
        dense
        :rows="rows"
        :cols="cols"
        :pagination="wholeTree"
        :global-items-per-page="false"
        :item-class="rowClass"
        :empty="empty"
        hide-pagination
        row-attr="path"
        data-testid="location-manager-table"
      >
        <template
          v-if="actionFailure || blockedDeletion"
          #body.prepend
        >
          <tr v-if="actionFailure">
            <td :colspan="cols.length">
              <FailureStrip
                in-table
                :title="t('location_manager.error')"
                :failure="actionFailure"
                data-testid="location-manager-error"
              />
            </td>
          </tr>
          <tr v-if="blockedDeletion">
            <td :colspan="cols.length">
              <LocationUsageNotice
                v-model="blockedDeletion"
                @archive="setArchived($event, true)"
              />
            </td>
          </tr>
        </template>
        <template #item.name="{ row }">
          <LocationTreeRowName
            :row="row"
            :search="search"
            @toggle="toggle(row.node.identifier)"
          />
          <InlineConfirm
            v-if="pendingDeletion?.identifier === row.node.identifier"
            class="my-1"
            :question="{
              confirmLabel: t('common.actions.delete'),
              message: t('location_manager.delete.message', { name: treeStore.pathLabelOf(row.node.identifier) }),
              title: t('location_manager.delete.title'),
              tone: 'error',
            }"
            :loading="deleting"
            data-testid="location-delete-confirm"
            @cancel="pendingDeletion = undefined"
            @confirm="confirmDeletion(row.node)"
          />
        </template>
        <template #item.actions="{ row }">
          <LocationTreeRowActions
            :node="row.node"
            @add-child="addBelow(row.node.identifier)"
            @toggle-archive="setArchived(row.node, row.node.isActive)"
            @edit="formData = { mode: 'edit', location: row.node }"
            @delete="requestDeletion(row.node)"
          />
        </template>
        <template
          v-if="search.trim()"
          #empty-description
        >
          <p class="text-body-2 text-rui-text-secondary">
            {{ t('location_manager.empty.search_description') }}
          </p>
          <RuiButton
            color="primary"
            variant="outlined"
            class="mt-2"
            data-testid="location-manager-create-from-search"
            @click="addBelow(ROOT_LOCATION, search.trim())"
          >
            {{ t('location_manager.empty.create', { name: search.trim() }) }}
          </RuiButton>
        </template>
      </RuiDataTable>
    </TableFrame>

    <KeepAlive>
      <LocationAliasesCard
        v-if="tab === 'aliases'"
        v-model:adding="addingAlias"
      />
    </KeepAlive>

    <LocationFormDialog
      v-model="formData"
      @saved="bringIntoView($event)"
    />
  </TablePageLayout>
</template>
