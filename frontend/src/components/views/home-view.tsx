"use client"

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Newspaper, Lock, BarChart3, ArrowRight } from "lucide-react"

interface HomeViewProps {
  onNavigate: (view: "module") => void
}

export function HomeView({ onNavigate }: HomeViewProps) {
  return (
    <div className="flex flex-1 flex-col">
      <header className="flex h-14 items-center border-b border-border bg-card px-8">
        <h1 className="text-sm font-medium text-foreground">Home</h1>
      </header>

      <main className="flex-1 px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Welcome back
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Select a module to get started with your tech watch workflow.
          </p>
        </div>

        <div className="grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card
            className="group cursor-pointer border-border transition-all hover:border-foreground/20 hover:shadow-md"
            onClick={() => onNavigate("module")}
          >
            <CardHeader>
              <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-primary">
                <Newspaper className="size-5 text-primary-foreground" />
              </div>
              <CardTitle className="text-base">Weekly News Bulletin</CardTitle>
              <CardDescription>
                Curate and distribute weekly tech news to your team.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                Open module
                <ArrowRight className="size-3" />
              </div>
            </CardContent>
          </Card>

          <Card className="cursor-not-allowed border-border opacity-50">
            <CardHeader>
              <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-muted">
                <BarChart3 className="size-5 text-muted-foreground" />
              </div>
              <CardTitle className="flex items-center gap-2 text-base">
                Trend Analysis
                <Lock className="size-3 text-muted-foreground" />
              </CardTitle>
              <CardDescription>
                Analyze technology trends over time.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <span className="text-xs font-medium text-muted-foreground">
                Coming soon
              </span>
            </CardContent>
          </Card>

          <Card className="cursor-not-allowed border-border opacity-50">
            <CardHeader>
              <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-muted">
                <BarChart3 className="size-5 text-muted-foreground" />
              </div>
              <CardTitle className="flex items-center gap-2 text-base">
                Report Generator
                <Lock className="size-3 text-muted-foreground" />
              </CardTitle>
              <CardDescription>
                Generate detailed technology reports.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <span className="text-xs font-medium text-muted-foreground">
                Coming soon
              </span>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
