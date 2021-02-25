export type BaseMessage = { success: string; error: string };

export function makeMessage(error: string = '', success: string = '') {
  return { success, error };
}

export type SettingsMessages<T extends string> = {
  [setting in T]: BaseMessage;
};

export const settingsMessages: <T extends string>(
  keys: ReadonlyArray<T>
) => SettingsMessages<T> = <T extends string>(keys: ReadonlyArray<T>) => {
  const settings: SettingsMessages<T> = {} as SettingsMessages<T>;
  for (const setting of keys) {
    settings[setting] = makeMessage();
  }
  return settings;
};
