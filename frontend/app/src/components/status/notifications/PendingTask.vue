<template>
  <card outlined :class="$style.task">
    <v-row no-gutters>
      <v-col>
        <div :class="$style.title">{{ task.meta.title }}</div>
      </v-col>
      <v-col cols="auto">
        <v-progress-circular
          size="20"
          width="2"
          :value="progress"
          :indeterminate="!isHistory"
          color="primary"
        />
      </v-col>
    </v-row>
    <v-row v-if="task.meta.description" no-gutters class="text--secondary">
      {{ task.meta.description }}
    </v-row>
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { setupReports } from '@/composables/reports';
import { Task, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';

export default defineComponent({
  name: 'PendingTask',
  props: {
    task: {
      required: true,
      type: Object as PropType<Task<TaskMeta>>
    }
  },
  setup(props) {
    const { task } = toRefs(props);
    const isHistory = computed(
      () => task.value.type === TaskType.TRADE_HISTORY
    );

    const { progress } = setupReports();
    return {
      isHistory,
      progress
    };
  }
});
</script>

<style module lang="scss">
.task {
  margin: 6px 0;
}

.title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
