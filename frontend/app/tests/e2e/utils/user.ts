import { Guid } from '../common/guid';

export function createUser() {
  const guid = Guid.newGuid().toString();
  return `test_${guid.substring(0, 6)}`;
}
