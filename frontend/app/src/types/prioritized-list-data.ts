export class PrioritizedListData<T = string> {
  constructor(private itemData: Array<PrioritizedListItemData<T>>) {}

  itemIdsNotIn(itemIds: T[]): T[] {
    return this.itemData
      .filter(item => !itemIds.includes(item.identifier))
      .map(itemData => itemData.identifier);
  }

  itemDataForId(id: T): PrioritizedListItemData<T> | undefined {
    return this.itemData.find(item => item.identifier === id);
  }
}

export interface PrioritizedListItemData<T = string> {
  identifier: T;
  icon?: string;
  extraDisplaySize?: string; // may be a string specifying pixels e.g. 12px
}
