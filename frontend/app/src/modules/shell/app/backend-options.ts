import type { Writeable } from '@rotki/common';
import { BackendOptions } from '@shared/ipc';

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

export const loadUserOptions: () => Partial<BackendOptions> = () => {
  try {
    const opts = localStorage.getItem(BACKEND_OPTIONS);
    let options: Writeable<Partial<BackendOptions>> = {};
    if (opts)
      options = BackendOptions.parse(JSON.parse(opts));
    return options;
  }
  catch {
    return {};
  }
};

export function saveUserOptions(config: Partial<BackendOptions>): void {
  const existingOptions = loadUserOptions();
  const updatedOptions = {
    ...existingOptions,
    ...config,
  };
  const options = JSON.stringify(updatedOptions);
  localStorage.setItem(BACKEND_OPTIONS, options);
}

export function clearUserOptions(): void {
  localStorage.removeItem(BACKEND_OPTIONS);
}
