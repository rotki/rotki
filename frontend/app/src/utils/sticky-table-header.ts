/**
 * This class is used for both table sticky header and horizontal scroll support on tables.
 * Source from https://github.com/archfz/vh-sticky-table-header
 * Modified to work with vuetify <v-data-table />
 */

class StickyTableHeader {
  private scrollListener?: EventListener;
  private sizeListener?: EventListener;
  private currentFrameRequest?: number;
  private containerScrollListener?: EventListener;
  private clickListener?: (event: MouseEvent) => any;
  private tableContainerParent: HTMLDivElement;
  private tableContainer: HTMLTableElement;
  private cloneContainer: HTMLTableElement;
  private cloneContainerParent: HTMLDivElement;
  private cloneHeader: any = null;
  private header: HTMLTableRowElement;
  private top: number;
  private mobileBreakpoint: number;
  private observer: ResizeObserver;

  constructor(
    tableContainer: HTMLTableElement,
    cloneContainer: HTMLTableElement,
    options: { top?: number; mobileBreakpoint?: number } = {}
  ) {
    this.tableContainer = tableContainer;
    this.cloneContainer = cloneContainer;
    this.top = options.top || 0;
    this.mobileBreakpoint = options.mobileBreakpoint || 0;
    this.observer = new ResizeObserver(() => this.checkPosition(true));

    this.header = this.getHeader();

    this.tableContainerParent = this.tableContainer
      .parentNode as HTMLDivElement;
    this.cloneContainerParent = this.cloneContainer
      .parentNode as HTMLDivElement;

    this.setup();
  }

  public destroy(): void {
    if (this.scrollListener) {
      document.body.removeEventListener('scroll', this.scrollListener);
    }
    if (this.sizeListener) {
      window.removeEventListener('resize', this.sizeListener);
    }
    if (this.currentFrameRequest) {
      window.cancelAnimationFrame(this.currentFrameRequest);
    }
    if (this.containerScrollListener) {
      this.tableContainerParent.removeEventListener(
        'click',
        this.containerScrollListener
      );
    }
    if (this.clickListener) {
      this.cloneContainer.removeEventListener('click', this.clickListener);
    }
    if (this.cloneHeader) {
      this.cloneContainer.removeChild(this.cloneHeader);
    }
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  private getHeader = () => {
    const header =
      this.tableContainer.querySelector<HTMLTableRowElement>('thead');

    if (!header || !this.tableContainer.parentNode) {
      throw new Error(
        'Header or parent node of sticky header table container not found!'
      );
    }

    this.observer.observe(header);

    return header;
  };

  private setupClickEventMirroring(): void {
    this.clickListener = (event: MouseEvent) => {
      const target = event.target;
      if (target && target instanceof HTMLElement) {
        const cellIndex = target.closest('th')?.cellIndex;

        if (cellIndex !== undefined) {
          const firstChild = this.header.querySelector(
            `th:nth-child(${cellIndex + 1}) > :first-child`
          );

          if (firstChild && firstChild instanceof HTMLElement) {
            firstChild.click();

            nextTick(() => {
              this.createClone();
              this.checkPosition(true);
            });
          }
        }
      }
    };

    this.cloneContainer.addEventListener('click', this.clickListener);
  }

  private adjustSize = () => {
    const headerSize = this.header.getBoundingClientRect().width;
    Array.from(this.header.children[0].children).forEach((cell, index) => {
      const percentageWidth =
        (cell.getBoundingClientRect().width / headerSize) * 100;

      this.cloneHeader.children[0].children[
        index
      ].style.width = `${percentageWidth}%`;
    });

    const tableContainerParentWidth =
      this.tableContainerParent.getBoundingClientRect().width;
    this.cloneContainerParent.style.width = `${tableContainerParentWidth}px`;

    const headerSizeInPx = `${headerSize}px`;
    this.cloneContainer.style.minWidth = headerSizeInPx;
    this.cloneContainer.style.width = headerSizeInPx;

    if (this.cloneContainer.nextElementSibling instanceof HTMLElement) {
      this.cloneContainer.nextElementSibling.style.width = headerSizeInPx;
    }
  };

  private checkPosition = (resize = false) => {
    const tableRect = this.tableContainer.getBoundingClientRect();

    const diffTop = -tableRect.y;
    const diffBottom = -this.getBottom();
    const top = this.getTop();

    const mobile = window.innerWidth <= this.mobileBreakpoint;

    let reCreated = false;
    if (resize && mobile) {
      this.removeClone();
    } else if (!mobile && diffTop > -top && this.cloneHeader === null) {
      this.createClone();
      reCreated = true;
    }

    if (this.cloneHeader !== null) {
      if (resize || reCreated) {
        this.adjustSize();
      }

      if (diffTop <= -top) {
        this.removeClone();
      } else if (diffBottom < -top) {
        this.cloneContainerParent.style.display = 'block';
        this.cloneContainerParent.style.top = `${top}px`;
        this.syncHorizontalScroll();
      } else {
        this.cloneContainerParent.style.display = 'none';
      }
    }
  };

  private setupSticky(): void {
    const updateSticky = (resize = false) => {
      this.currentFrameRequest = window.requestAnimationFrame(() => {
        this.checkPosition(resize);
      });
    };
    this.scrollListener = () => updateSticky();
    this.sizeListener = () => updateSticky(true);
    updateSticky(true);

    document.body.addEventListener('scroll', this.scrollListener);
    window.addEventListener('resize', this.sizeListener);
  }

  private setup(): void {
    this.setupSticky();
    this.setupClickEventMirroring();
    this.setupHorizontalScrollMirroring();
  }

  private setupHorizontalScrollMirroring(): void {
    this.containerScrollListener = () => {
      window.requestAnimationFrame(() => {
        this.syncHorizontalScroll();
      });
    };

    this.tableContainerParent.addEventListener(
      'scroll',
      this.containerScrollListener
    );
  }

  private removeClone(): void {
    if (this.cloneHeader) {
      this.cloneContainerParent.style.display = 'none';
      this.cloneContainer.removeChild(this.cloneHeader);
      this.cloneHeader = null;
    }
  }

  private createClone(): void {
    this.header = this.getHeader();

    if (this.header.classList.contains('v-data-table-header-mobile')) {
      this.removeClone();
      return;
    }

    const clone = this.header.cloneNode(true);
    this.cloneContainer.replaceChildren(clone);

    this.cloneHeader = clone;
  }

  private syncHorizontalScroll(): void {
    this.cloneContainerParent.scrollLeft = this.tableContainerParent.scrollLeft;
  }

  private getTop(): number {
    return Math.max(this.top, document.body.getBoundingClientRect().top);
  }

  private getBottom(): number {
    const tableRect = this.tableContainer.getBoundingClientRect();
    const headerHeight = this.header.getBoundingClientRect().height;

    const defaultBottom = tableRect.y + tableRect.height - headerHeight;
    const parentBottom =
      document.body.getBoundingClientRect().bottom - 2 * headerHeight;
    return Math.min(defaultBottom, parentBottom, Number.MAX_VALUE);
  }
}

export default StickyTableHeader;
