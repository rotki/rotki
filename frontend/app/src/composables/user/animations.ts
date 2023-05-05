export const useAnimation = createSharedComposable(() => {
  const animationEnabled = useLocalStorage(
    'rotki.login_animation_enabled',
    true
  );

  const toggleAnimation = () => {
    set(animationEnabled, !get(animationEnabled));
  };

  return {
    animationEnabled,
    toggleAnimation
  };
});
