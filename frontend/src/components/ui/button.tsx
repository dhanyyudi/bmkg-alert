import * as React from "react"
import { type VariantProps, cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

// Simplified CVA-like pattern without the dependency if possible, but cva is standard.
// Since I didn't install cva, I'll write a manual implementation or install it. 
// Actually, `npm install class-variance-authority` is standard. 
// I'll stick to manual cn() composition for now to avoid installing more deps if checking status is slow, 
// BUT users expect Shadcn-like quality. I'll implement a robust one manually.

const buttonVariants = (variant: string = "default", size: string = "default", className?: string) => {
    const base = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background";
    
    const variants: Record<string, string> = {
        default: "bg-primary-600 text-white hover:bg-primary-700",
        destructive: "bg-red-500 text-white hover:bg-red-600",
        outline: "border border-input hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-accent-foreground",
        link: "underline-offset-4 hover:underline text-primary",
    };

    const sizes: Record<string, string> = {
        default: "h-10 py-2 px-4",
        sm: "h-9 px-3 rounded-md",
        lg: "h-11 px-8 rounded-md",
        icon: "h-10 w-10",
    };

    return cn(base, variants[variant] || variants.default, sizes[size] || sizes.default, className);
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
    size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={buttonVariants(variant, size, className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
