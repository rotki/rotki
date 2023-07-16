<script setup lang="ts">
import dayjs from 'dayjs';
import { type Task, type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

const props = defineProps<{ task: Task<TaskMeta> }>();

const css = useCssModule();

const { task } = toRefs(props);
const isHistory = computed(() => task.value.type === TaskType.TRADE_HISTORY);

const { progress } = storeToRefs(useReportsStore());

const time = computed(() => dayjs(task.value.time).format('LLL'));
</script>

<template>
  <Card outlined :class="css.task">
    <VRow align="center" no-gutters class="flex-nowrap">
      <VCol>
        <VRow no-gutters>
          <VCol>
            <div :class="css.title" class="text--primary">
              {{ task.meta.title }}
            </div>
          </VCol>
        </VRow>
        <VRow
          v-if="task.meta.description"
          no-gutters
          :class="css.description"
          class="text--secondary"
        >
          {{ task.meta.description }}
        </VRow>
        <VRow class="text-caption px-3" :class="css.date">
          {{ time }}
        </VRow>
      </VCol>
      <VCol cols="auto">
        <VProgressCircular
          v-if="isHistory"
          size="20"
          width="2"
          :value="progress"
          color="primary"
        />
        <VIcon v-else color="primary">mdi-spin mdi-loading</VIcon>
      </VCol>
    </VRow>
  </Card>
</template>

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
