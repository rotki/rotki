<template>
  <card outlined :class="$style.task">
    <v-row align="center" no-gutters class="flex-nowrap">
      <v-col>
        <v-row no-gutters>
          <v-col>
            <div :class="$style.title" class="text--primary">
              {{ task.meta.title }}
            </div>
          </v-col>
        </v-row>
        <v-row
          v-if="task.meta.description"
          no-gutters
          :class="$style.description"
          class="text--secondary"
        >
          {{ task.meta.description }}
        </v-row>
        <v-row class="text-caption px-3" :class="$style.date">
          {{ time }}
        </v-row>
      </v-col>
      <v-col cols="auto">
        <v-progress-circular
          v-if="isHistory"
          size="20"
          width="2"
          :value="progress"
          color="primary"
        />
        <v-icon v-else color="primary">mdi-spin mdi-loading</v-icon>
      </v-col>
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
import dayjs from 'dayjs';
import { storeToRefs } from 'pinia';
import { useReports } from '@/store/reports';
import { Task, TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

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

    const { progress } = storeToRefs(useReports());

    const time = computed(() => {
      return dayjs(task.value.time).format('LLL');
    });

    return {
      time,
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
  font-size: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.description {
  font-size: 0.8rem;
  white-space: pre-line;
}

.date {
  font-size: 0.75rem;
}
</style>
