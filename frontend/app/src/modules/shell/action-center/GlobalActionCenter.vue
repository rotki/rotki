<script setup lang="ts">
import { startPromise } from '@shared/utils';
import ActionCenterList from '@/modules/core/action-center/ActionCenterList.vue';
import ActionCenterMenu from '@/modules/core/action-center/ActionCenterMenu.vue';
import { useOpenActionTarget } from '@/modules/core/action-center/use-open-action-target';
import { useGlobalActionCenter } from '@/modules/shell/action-center/use-global-action-center';

const open = ref<boolean>(false);

const { checking, cleared, count, refreshAll, refreshing, sections } = useGlobalActionCenter();
const { openTarget } = useOpenActionTarget();

function close(): void {
  set(open, false);
}
</script>

<template>
  <ActionCenterMenu
    v-model="open"
    :count="count"
    :checking="checking"
    badge
  >
    <ActionCenterList
      :sections="sections"
      :cleared="cleared"
      :count="count"
      :checking="checking"
      :refreshing="refreshing"
      @open="openTarget($event, close)"
      @refresh="startPromise(refreshAll())"
    />
  </ActionCenterMenu>
</template>
