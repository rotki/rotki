import type { Ref } from 'vue';
import { cloneDeep, isEqual } from 'es-toolkit';

export interface EditModeStateTracker {
  editModeStateSnapshot: Ref<Record<string, any> | undefined>;
  captureEditModeState: (state: Record<string, any>) => void;
  captureEditModeStateFromRefs: (statesRefs: Record<string, Ref<any>>) => void;
  hasEditModeStateChanged: (currentState: Record<string, any>) => boolean;
  shouldSkipSave: (isEditMode: boolean, currentState: Record<string, any>) => boolean;
  shouldSkipSaveFromRefs: (isEditMode: boolean, statesRefs: Record<string, Ref<any>>) => boolean;
}

/**
 * Composable for tracking state changes in edit mode to prevent unnecessary saves
 * when no changes have been made to the form data.
 */
export function useEditModeStateTracker(): EditModeStateTracker {
  const editModeStateSnapshot = ref<Record<string, any>>();

  /**
   * Captures the current state as a snapshot for later comparison
   */
  function captureEditModeState(state: Record<string, any>): void {
    set(editModeStateSnapshot, cloneDeep(state));
  }

  /**
   * Helper function to unwrap all ref values from a states object
   */
  function unwrapStatesRefs(statesRefs: Record<string, Ref<any>>): Record<string, any> {
    const unwrapped: Record<string, any> = {};
    for (const [key, ref] of Object.entries(statesRefs)) {
      unwrapped[key] = get(ref);
    }
    return unwrapped;
  }

  /**
   * Captures the current state from a states refs object for later comparison
   */
  function captureEditModeStateFromRefs(statesRefs: Record<string, Ref<any>>): void {
    captureEditModeState(unwrapStatesRefs(statesRefs));
  }

  /**
   * Checks if the current state differs from the captured snapshot
   */
  function hasEditModeStateChanged(currentState: Record<string, any>): boolean {
    const snapshot = get(editModeStateSnapshot);
    if (!snapshot) {
      return true; // No snapshot means we should save
    }
    return !isEqual(currentState, snapshot);
  }

  /**
   * Determines if the save operation should be skipped based on edit mode and state changes
   */
  function shouldSkipSave(isEditMode: boolean, currentState: Record<string, any>): boolean {
    return isEditMode && !hasEditModeStateChanged(currentState);
  }

  /**
   * Determines if the save operation should be skipped based on edit mode and state changes from refs
   */
  function shouldSkipSaveFromRefs(isEditMode: boolean, statesRefs: Record<string, Ref<any>>): boolean {
    return shouldSkipSave(isEditMode, unwrapStatesRefs(statesRefs));
  }

  return {
    captureEditModeState,
    captureEditModeStateFromRefs,
    editModeStateSnapshot,
    hasEditModeStateChanged,
    shouldSkipSave,
    shouldSkipSaveFromRefs,
  };
}
