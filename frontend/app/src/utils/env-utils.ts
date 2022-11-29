export const checkIfDevelopment = (): boolean => {
  return import.meta.env.DEV;
};
