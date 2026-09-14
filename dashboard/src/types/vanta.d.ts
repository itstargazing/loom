declare module "vanta/dist/vanta.net.min" {
  const effect: (opts: Record<string, unknown>) => {
    destroy: () => void;
    resize?: () => void;
    setOptions?: (opts: Record<string, unknown>) => void;
  };
  export default effect;
}

declare module "vanta/dist/vanta.fog.min" {
  const effect: (opts: Record<string, unknown>) => {
    destroy: () => void;
    resize?: () => void;
    setOptions?: (opts: Record<string, unknown>) => void;
  };
  export default effect;
}

declare module "vanta/dist/vanta.waves.min" {
  const effect: (opts: Record<string, unknown>) => {
    destroy: () => void;
    resize?: () => void;
    setOptions?: (opts: Record<string, unknown>) => void;
  };
  export default effect;
}

declare module "vanta/dist/vanta.dots.min" {
  const effect: (opts: Record<string, unknown>) => {
    destroy: () => void;
    resize?: () => void;
    setOptions?: (opts: Record<string, unknown>) => void;
  };
  export default effect;
}
