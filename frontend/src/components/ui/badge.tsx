import * as React from "react"
import { cn } from "@/lib/utils"

const badgeVariants = (variant: string = "default", className?: string) => {
    const variants: Record<string, string> = {
        default: "border-transparent bg-primary-500 text-white hover:bg-primary-500/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-red-500 text-white hover:bg-red-500/80",
        outline: "text-foreground",
        // Severity variants
        low: "border-transparent bg-emerald-500 text-white",
        moderate: "border-transparent bg-amber-500 text-white",
        severe: "border-transparent bg-orange-600 text-white",
        extreme: "border-transparent bg-red-600 text-white",
    };
    
    return cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variants[variant] || variants.default,
        className
    );
}

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "secondary" | "destructive" | "outline" | "low" | "moderate" | "severe" | "extreme";
}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={badgeVariants(variant, className)} {...props} />
  )
}

export { Badge, badgeVariants }
