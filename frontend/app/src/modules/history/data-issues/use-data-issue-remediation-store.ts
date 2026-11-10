/**
 * State-only record of the periodic auto-remediation job.
 *
 * The websocket progress handler bumps the counter when a run finishes and the inbox reacts to
 * it: the list and its badge reload then, since that run is what resolves or re-states the issues.
 * A counter rather than a boolean, so two runs ending back to back both reload.
 */
export const useDataIssueRemediationStore = defineStore('history/data-issue-remediation', () => {
  const remediationCompleted = ref<number>(0);

  function notifyRemediationCompleted(): void {
    set(remediationCompleted, get(remediationCompleted) + 1);
  }

  return {
    notifyRemediationCompleted,
    remediationCompleted,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useDataIssueRemediationStore, import.meta.hot));
