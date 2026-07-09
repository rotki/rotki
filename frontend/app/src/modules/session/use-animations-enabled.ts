/**
 * Shared, global instance of the `animationsEnabled` session setting's localStorage backing
 * (`rotki.animations_enabled`).
 *
 * It is declared as the `animationsEnabled` registry entry's `mirror`, so writing the setting through
 * the normal settings pipeline keeps localStorage in sync (no bespoke setter needed). The settings
 * repo also reads it to seed the session default on boot, which is what makes the toggle persist
 * across restarts.
 */
export const useAnimationsEnabled = createSharedComposable(() => useLocalStorage<boolean>('rotki.animations_enabled', true));
