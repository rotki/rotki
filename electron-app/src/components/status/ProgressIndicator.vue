<template>
  <v-menu id="notification-indicator" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-badge>
        <v-btn color="primary" dark icon text v-on="on">
          <v-icon v-if="hasRunningTasks" class="top-loading-icon">
            fa fa-circle-o-notch fa-spin
          </v-icon>
          <v-icon v-else>
            fa fa-check-circle
          </v-icon>
        </v-btn>
      </v-badge>
    </template>
    <v-layout column class="progress-indicator__details">
      <v-list v-if="tasks.length > 0" shaped>
        <v-list-item v-for="task in tasks" :key="task.id">
          <v-list-item-content>
            <v-list-item-title v-text="task.description"></v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>
      <div v-else class="progress-indicator__no_tasks">
        <v-icon color="primary">fa fa-info-circle</v-icon>
        <div>No running tasks</div>
      </div>
    </v-layout>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Task } from '@/model/task';

const { mapGetters } = createNamespacedHelpers('tasks');

@Component({
  computed: {
    ...mapGetters(['hasRunningTasks', 'tasks'])
  }
})
export default class ProgressIndicator extends Vue {
  hasRunningTasks!: boolean;
  tasks!: Task[];
}
</script>

<style scoped lang="scss">
.progress-indicator__details {
  width: 300px;
  height: 350px;
  background-color: white;
}
</style>
