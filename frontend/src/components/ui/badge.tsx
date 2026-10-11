import * as React from "react"
import { cn } from "@/lib/utils"

const badgeVariants = (variant: string = "default", className?: string) => {
    const variants: Record<string, string> = {
        default: "border-transparent bg-primary-700 text-white",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
    };

    return cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        variants[variant] || variants.default,
        className
    );
}

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "secondary" | "outline";
}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={badgeVariants(variant, className)} {...props} />
  )
}

export { Badge, badgeVariants }
