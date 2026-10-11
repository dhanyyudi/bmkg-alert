import * as React from "react"
import { cn } from "@/lib/utils"

const buttonVariants = (variant: string = "default", size: string = "default", className?: string) => {
    const base = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background disabled:opacity-50 disabled:cursor-not-allowed";

    const variants: Record<string, string> = {
        default: "bg-primary-700 text-white hover:bg-primary-800",
        destructive: "bg-red-600 text-white hover:bg-red-700",
        outline: "border border-input bg-card text-card-foreground hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "underline-offset-4 hover:underline text-primary dark:text-sky-400",
    };

    // 44px touch targets on phones, the denser desktop sizes from md up
    const sizes: Record<string, string> = {
        default: "h-11 md:h-10 py-2 px-4",
        sm: "h-11 md:h-9 px-3",
        lg: "h-11 px-8",
        icon: "h-11 w-11 md:h-10 md:w-10",
    };

    return cn(base, variants[variant] || variants.default, sizes[size] || sizes.default, className);
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
    size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = "button", ...props }, ref) => {
    return (
      <button
        type={type}
        className={buttonVariants(variant, size, className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
