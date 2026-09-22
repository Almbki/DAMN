import { createContext, useContext, useEffect } from 'react';

/**
 * A slot that lets a page put its own controls into the shell's top bar.
 *
 * The shell owns the header state; a page registers the two control nodes it
 * wants shown. The context carries only the (stable) setter, never the current
 * controls, so a header update cannot re-render the page that registered it —
 * which is what keeps this from turning into a render loop.
 *
 * Pages build their controls with `useMemo` keyed on the state that actually
 * changes, so the effect below only fires when the header really needs updating.
 */

export type HeaderControls = {
  left?: React.ReactNode;
  right?: React.ReactNode;
};

type HeaderControlsSetter = (controls: HeaderControls) => void;

export const HeaderControlsContext = createContext<HeaderControlsSetter | null>(null);

/** Register the controls for the current page; cleared when the page unmounts. */
export function useHeaderControls(controls: HeaderControls) {
  const setControls = useContext(HeaderControlsContext);
  useEffect(() => {
    if (!setControls) return;
    setControls(controls);
    return () => setControls({});
  }, [controls, setControls]);
}
