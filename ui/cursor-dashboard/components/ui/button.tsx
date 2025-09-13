import * as React from "react";

export type Size = "sm" | "md" | "lg" | "icon";
export type Variant = "default" | "outline" | "ghost";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

type ButtonVariantOptions = { variant?: Variant; size?: Size };

/**
 * Backwards-compatible:
 * - buttonVariants("outline", "md")
 * - buttonVariants({ variant: "outline", size: "md" })
 */
export function buttonVariants(
  a?: Variant | ButtonVariantOptions,
  b?: Size
) {
  let variant: Variant = "default";
  let size: Size = "md";

  if (typeof a === "string") {
    variant = a;
    size = b ?? "md";
  } else if (a && typeof a === "object") {
    variant = a.variant ?? "default";
    size = a.size ?? "md";
  }

  const base =
    "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none";
  const variants: Record<Variant, string> = {
    default: "bg-white/10 hover:bg-white/20 border border-white/10",
    outline: "border border-white/20 hover:bg-white/5",
    ghost: "hover:bg-white/5",
  };
  const sizes: Record<Size, string> = {
    sm: "h-8 px-2 text-xs",
    md: "h-9 px-3 text-sm",
    lg: "h-10 px-4 text-base",
    icon: "h-9 w-9 p-0",
  };

  return [base, variants[variant], sizes[size]].join(" ");
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", ...props }, ref) => {
    return (
      <button
        className={[buttonVariants(variant, size), className].filter(Boolean).join(" ")}
        ref={ref}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";

export default Button;
