import { useEffect, type RefObject } from 'react';

export function useDialogFocus(ref: RefObject<HTMLElement | null>, active: boolean, trap = false) {
  useEffect(() => {
    if (!active || !ref.current) return;
    const previous = document.activeElement as HTMLElement | null;
    const element = ref.current;
    const focusable = () => [...element.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], textarea, input, [tabindex="0"]')];
    (focusable()[0] ?? element).focus();
    function keydown(event: KeyboardEvent) {
      if (!trap || event.key !== 'Tab') return;
      const nodes = focusable();
      const first = nodes[0]; const last = nodes.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    element.addEventListener('keydown', keydown);
    return () => { element.removeEventListener('keydown', keydown); if (previous?.isConnected) previous.focus(); };
  }, [ref, active, trap]);
}
