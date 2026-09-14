"use client";

import Image from "next/image";

/** Cache-busted brand mark so auth/dashboard pick up the new horned logo. */
const LOGO_SRC = "/brand/loom-mark-flat.png?v=horn-1";

const SIZES = {
  sm: { width: 40, height: 30 },
  md: { width: 56, height: 43 },
  lg: { width: 96, height: 73 },
} as const;

type BrandLogoProps = {
  size?: keyof typeof SIZES;
  className?: string;
};

export function BrandLogo({ size = "md", className = "" }: BrandLogoProps) {
  const dim = SIZES[size];

  return (
    <Image
      src={LOGO_SRC}
      alt="LOOM"
      width={dim.width}
      height={dim.height}
      unoptimized
      className={["h-auto w-auto bg-transparent select-none", className]
        .filter(Boolean)
        .join(" ")}
      priority={size === "lg"}
    />
  );
}
