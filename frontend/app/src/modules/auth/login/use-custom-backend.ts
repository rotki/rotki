import type { ComputedRef, Ref } from 'vue';
import { deleteBackendUrl, getBackendUrl, saveBackendUrl } from '@/modules/auth/account-management';

export type ServerColor = 'primary' | 'success' | undefined;

interface UseCustomBackendOptions {
  /** Notified whenever the configured backend changes; `null` means the override was cleared. */
  onChange: (url: string | null) => void;
}

interface UseCustomBackendReturn {
  /** Bound to the backend URL field. */
  modelUrl: Ref<string>;
  /** Bound to the "session only" checkbox. */
  modelSessionOnly: Ref<boolean>;
  /** Whether the backend settings panel is expanded. */
  display: Readonly<Ref<boolean>>;
  /** Whether a backend override is currently persisted. */
  saved: Readonly<Ref<boolean>>;
  /** Tints the server icon to signal a session-only or persisted override. */
  serverColor: ComputedRef<ServerColor>;
  /** Restores the persisted backend override into the form. */
  loadBackendSettings: () => void;
  /** Persists the entered backend URL and collapses the panel. */
  saveBackend: () => void;
  /** Removes the persisted backend override and collapses the panel. */
  clearBackend: () => void;
  /** Expands or collapses the backend settings panel. */
  toggleDisplay: () => void;
}

/**
 * Owns the login form's custom-backend override: the URL being edited, whether it is
 * session-only, and whether the settings panel is expanded.
 *
 * Saving and clearing both write through to the persisted backend URL and notify the
 * caller, so the two stay in step without the component coordinating them.
 */
export function useCustomBackend(options: UseCustomBackendOptions): UseCustomBackendReturn {
  const { onChange } = options;

  // `model` prefix marks these as intentionally writable: both are bound with v-model.
  const modelUrl = shallowRef<string>('');
  const modelSessionOnly = shallowRef<boolean>(false);
  const display = shallowRef<boolean>(false);
  const saved = shallowRef<boolean>(false);

  const serverColor = computed<ServerColor>(() => {
    if (get(modelSessionOnly))
      return 'primary';
    else if (get(saved))
      return 'success';

    return undefined;
  });

  function loadBackendSettings(): void {
    const { sessionOnly, url } = getBackendUrl();
    set(modelUrl, url);
    set(modelSessionOnly, sessionOnly);
    set(saved, !!url);
  }

  function saveBackend(): void {
    saveBackendUrl({
      sessionOnly: get(modelSessionOnly),
      url: get(modelUrl),
    });
    onChange(get(modelUrl));
    set(saved, true);
    set(display, false);
  }

  function clearBackend(): void {
    set(modelUrl, '');
    set(modelSessionOnly, false);
    deleteBackendUrl();
    onChange(null);
    set(saved, false);
    set(display, false);
  }

  function toggleDisplay(): void {
    set(display, !get(display));
  }

  return {
    clearBackend,
    display: readonly(display),
    loadBackendSettings,
    modelSessionOnly,
    modelUrl,
    saveBackend,
    saved: readonly(saved),
    serverColor,
    toggleDisplay,
  };
}
