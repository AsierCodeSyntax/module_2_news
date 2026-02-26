"use client"

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Zap, FileText, PlusCircle, ArrowRight } from "lucide-react"

type View = "home" | "module" | "add-news" | "review"

interface ModuleViewProps {
  onNavigate: (view: View) => void
}

const actions = [
  {
    title: "Run Automatic Generation",
    description: "Scrape, evaluate, and compile the latest tech news automatically.",
    icon: Zap,
    view: "module" as View,
    badge: "Auto",
  },
  {
    title: "Review Latest Bulletin",
    description: "Review, edit, and approve the generated news bulletin before sending.",
    icon: FileText,
    view: "review" as View,
    badge: null,
  },
  {
    title: "Add Manual News",
    description: "Manually submit an article URL to be evaluated and added to the bulletin.",
    icon: PlusCircle,
    view: "add-news" as View,
    badge: null,
  },
]

export function ModuleView({ onNavigate }: ModuleViewProps) {
  return (
    <div className="flex flex-1 flex-col">
      <header className="flex h-14 items-center gap-3 border-b border-border bg-card px-8">
        <button
          onClick={() => onNavigate("home")}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          Home
        </button>
        <span className="text-sm text-muted-foreground">/</span>
        <h1 className="text-sm font-medium text-foreground">
          Weekly News Bulletin
        </h1>
      </header>

      <main className="flex-1 px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            News Bulletin
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your weekly technology news bulletin workflow.
          </p>
        </div>

        <div className="grid max-w-4xl grid-cols-1 gap-4 md:grid-cols-3">
          {actions.map((action) => {
            const Icon = action.icon
            return (
              <Card
                key={action.title}
                className="group cursor-pointer border-border transition-all hover:border-foreground/20 hover:shadow-md"
                onClick={() => onNavigate(action.view)}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex size-10 items-center justify-center rounded-lg bg-primary">
                      <Icon className="size-5 text-primary-foreground" />
                    </div>
                    {action.badge && (
                      <Badge variant="secondary" className="text-[10px]">
                        {action.badge}
                      </Badge>
                    )}
                  </div>
                  <CardTitle className="mt-2 text-base">{action.title}</CardTitle>
                  <CardDescription>{action.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                    {action.title === "Run Automatic Generation"
                      ? "Start pipeline"
                      : action.title === "Review Latest Bulletin"
                      ? "Open review"
                      : "Add article"}
                    <ArrowRight className="size-3" />
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </main>
    </div>
  )
}
