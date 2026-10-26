type Name = 'home' | 'parts' | 'design' | 'strategy' | 'components' | 'settings' | 'close' | 'expand' | 'collapse' | 'focus' | 'reset' | 'arrow' | 'chevron' | 'check' | 'orbit' | 'info';
const paths: Record<Name, string> = {
  home: 'M3 10 12 3l9 7M5 9v12h5v-7h4v7h5V9',
  parts: 'm12 3 9 5-9 5-9-5 9-5ZM3 8v9l9 5 9-5V8M12 13v9',
  design:'M5 19 14 5h5L10 19ZM5 15 14 1M15 5v8M19 5v8M3 19h9M5 17v4M10 17v4M13 13h8',
  strategy:'M3 18h5v-5h7V6h6M3 15v6h6M18 3h4v6M12 10l3 3-3 3',
  components:'M3 6h18v12H3ZM7 10v4M12 10v4M17 10v4M3 4v16M21 4v16',
  settings: 'M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M9 15v6',
  close: 'm6 6 12 12M6 18 18 6', expand: 'M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5',
  collapse: 'M3 8h5V3M21 8h-5V3M8 21v-5H3M16 21v-5h5',
  focus: 'M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5M9 12h6M12 9v6',
  reset: 'M3 10a9 9 0 1 1 2 8M3 4v6h6', arrow: 'M5 12h14m-6-6 6 6-6 6',
  chevron: 'm8 4 8 8-8 8', check: 'm5 12 4 4L19 6',
  orbit: 'M20 8c-3-5-11-6-15-1s-2 12 4 14M4 16c4 4 13 2 16-4S16 1 11 3M12 10v4m-2-2h4',
  info: 'M12 11v6M12 7v.1M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
};
export function Icon({ name, size = 18 }: { name: Name; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
