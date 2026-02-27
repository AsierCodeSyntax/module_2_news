"use client"

import { useState } from "react"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Zap, FileText, PlusCircle, ArrowRight, Loader2, Archive } from "lucide-react"
type View = "home" | "module" | "add-news" | "review"

interface ModuleViewProps {
  onNavigate: (view: View) => void
}

export function ModuleView({ onNavigate }: ModuleViewProps) {
  const [isRunning, setIsLoading] = useState(false)

  // Función que llama a la API de Python para arrancar el pipeline
  async function handleRunPipeline() {
    setIsLoading(true)
    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"
      const response = await fetch(`${API_URL}/api/bulletin/run`, {
        method: "POST"
      })
      if (!response.ok) throw new Error("Error en la ejecución")

      alert("¡Borrador generado con éxito! Puedes ir a revisarlo.")
    } catch (error) {
      console.error("Error:", error)
      alert("Hubo un error al ejecutar el pipeline.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex h-14 items-center gap-3 border-b border-border bg-card px-8">
        <button onClick={() => onNavigate("home")} className="text-sm text-muted-foreground transition-colors hover:text-foreground">
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

          {/* BOTÓN 1: RUN PIPELINE */}
          <Card
            className={`group cursor-pointer border-border transition-all hover:border-foreground/20 hover:shadow-md ${isRunning ? 'opacity-70 pointer-events-none' : ''}`}
            onClick={handleRunPipeline}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary">
                  {isRunning ? <Loader2 className="size-5 text-primary-foreground animate-spin" /> : <Zap className="size-5 text-primary-foreground" />}
                </div>
                <Badge variant="secondary" className="text-[10px]">Auto</Badge>
              </div>
              <CardTitle className="mt-2 text-base">Run Automatic Generation</CardTitle>
              <CardDescription>Scrape, evaluate, and compile the latest tech news automatically.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                {isRunning ? "Running pipeline in backend..." : "Start pipeline"}
                {!isRunning && <ArrowRight className="size-3" />}
              </div>
            </CardContent>
          </Card>

          {/* BOTÓN 2: REVIEW */}
          <Card
            className="group cursor-pointer border-border transition-all hover:border-foreground/20 hover:shadow-md"
            onClick={() => onNavigate("review")}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary">
                  <FileText className="size-5 text-primary-foreground" />
                </div>
              </div>
              <CardTitle className="mt-2 text-base">Review Latest Bulletin</CardTitle>
              <CardDescription>Review, edit, and approve the generated news bulletin before sending.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                Open review
                <ArrowRight className="size-3" />
              </div>
            </CardContent>
          </Card>

          {/* BOTÓN 3: ADD MANUAL */}
          <Card
            className="group cursor-pointer border-border transition-all hover:border-foreground/20 hover:shadow-md"
            onClick={() => onNavigate("add-news")}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary">
                  <PlusCircle className="size-5 text-primary-foreground" />
                </div>
              </div>
              <CardTitle className="mt-2 text-base">Add Manual News</CardTitle>
              <CardDescription>Manually submit an article URL to be evaluated and added to the bulletin.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                Add article
                <ArrowRight className="size-3" />
              </div>
            </CardContent>
          </Card>
          {/* BOTÓN 4: ARCHIVE */}
          <Card
            className="group cursor-pointer border-border transition-all hover:border-foreground/20 hover:shadow-md"
            onClick={() => onNavigate("archive")}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary">
                  <Archive className="size-5 text-primary-foreground" />
                </div>
              </div>
              <CardTitle className="mt-2 text-base">Bulletin Archive</CardTitle>
              <CardDescription>Browse, preview, and download previously published weekly bulletins.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                View archive
                <ArrowRight className="size-3" />
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}