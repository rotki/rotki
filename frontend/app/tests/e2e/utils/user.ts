import { Guid } from '../common/guid';

export const createUser = () => {
  const guid = Guid.newGuid().toString();
  return `test_${guid.substring(0, 6)}`;
};
