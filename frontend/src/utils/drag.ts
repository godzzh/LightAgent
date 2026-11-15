export type DragStyleOptions = Partial<
    Pick<CSSStyleDeclaration, 'left' | 'top' | 'right' | 'bottom' | 'position' | 'transform'>
>;

/** 拖拽手柄内部的可交互控件：在它们上面按下鼠标属于点击，不应启动拖拽。 */
const INTERACTIVE_SELECTOR = [
    'button', 'a[href]', 'input', 'select', 'textarea', 'label',
    '[role="button"]', '[role="switch"]', '[role="checkbox"]', '[contenteditable="true"]',
].join(',');

/** 移动超过该像素才认定是一次拖拽，避免「点一下标题」也改动布局。 */
const DRAG_THRESHOLD = 3;

/** 通过指定拖拽手柄移动其父元素，并把活动范围限制在当前视口。 */
class Drag {
    private readonly handle: HTMLElement;
    private readonly target: HTMLElement;

    constructor(handle: HTMLElement, options: DragStyleOptions = {}) {
        if (!(handle.parentElement instanceof HTMLElement)) {
            throw new Error('v-drag 必须挂载在具有 HTMLElement 父节点的拖拽手柄上');
        }
        this.handle = handle;
        this.target = handle.parentElement;
        this.handle.style.cursor = 'move';
        Object.assign(this.target.style, options);
        this.handle.addEventListener('pointerdown', this.handlePointerDown);
    }

    destroy() {
        this.handle.removeEventListener('pointerdown', this.handlePointerDown);
    }

    private readonly handlePointerDown = (event: PointerEvent) => {
        if (event.button !== 0) return;
        if (event.target instanceof Element && event.target.closest(INTERACTIVE_SELECTOR)) return;
        event.preventDefault();
        const startRect = this.target.getBoundingClientRect();
        const startX = event.clientX;
        const startY = event.clientY;
        let started = false;

        const beginDrag = () => {
            started = true;
            this.target.style.right = 'auto';
            this.target.style.bottom = 'auto';
            if (window.getComputedStyle(this.target).transform !== 'none') {
                this.target.style.transform = 'none';
            }
            this.target.style.position = this.target.style.position || 'fixed';
            this.target.style.left = `${startRect.left}px`;
            this.target.style.top = `${startRect.top}px`;
        };

        const handleMove = (moveEvent: PointerEvent) => {
            if (!started) {
                const movedX = Math.abs(moveEvent.clientX - startX);
                const movedY = Math.abs(moveEvent.clientY - startY);
                if (movedX < DRAG_THRESHOLD && movedY < DRAG_THRESHOLD) return;
                beginDrag();
            }
            const maxLeft = Math.max(0, window.innerWidth - startRect.width);
            const maxTop = Math.max(0, window.innerHeight - startRect.height);
            const left = Math.min(maxLeft, Math.max(0, startRect.left + moveEvent.clientX - startX));
            const top = Math.min(maxTop, Math.max(0, startRect.top + moveEvent.clientY - startY));
            this.target.style.left = `${left}px`;
            this.target.style.top = `${top}px`;
        };
        const handleUp = () => {
            window.removeEventListener('pointermove', handleMove);
            window.removeEventListener('pointerup', handleUp);
            window.removeEventListener('pointercancel', handleUp);
        };

        window.addEventListener('pointermove', handleMove);
        window.addEventListener('pointerup', handleUp, { once: true });
        window.addEventListener('pointercancel', handleUp, { once: true });
    };
}

export default Drag;
