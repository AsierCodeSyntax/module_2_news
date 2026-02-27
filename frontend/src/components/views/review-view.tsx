"use client"

import { useState, useEffect } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Trash2, FileText, Mail, CheckCircle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

type View = "home" | "module" | "add-news" | "review"

interface NewsArticle {
  id: number
  title: string
  topic: string
  summary_short: string
  llm_score: number
  url: string
}

interface ReviewViewProps {
  onNavigate: (view: View) => void
}

const topicColors: Record<string, string> = {
  plone: "bg-[oklch(0.55_0.15_220)] text-[oklch(0.985_0_0)]",
  django: "bg-[oklch(0.52_0.17_152)] text-[oklch(0.985_0_0)]",
  ai: "bg-[oklch(0.55_0.2_280)] text-[oklch(0.985_0_0)]",
}

export function ReviewView({ onNavigate }: ReviewViewProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [pdfTimestamp, setPdfTimestamp] = useState(Date.now())
  const [isSending, setIsSending] = useState(false)
  // URL base de tu API
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

  // Cargar el JSON del servidor nada más abrir la página
  useEffect(() => {
    fetchBulletinData()
  }, [])

  async function fetchBulletinData() {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/bulletin/latest`)
      if (!response.ok) throw new Error("No hay boletín generado todavía.")

      const data = await response.json()

      // El JSON está agrupado por topics, lo aplanamos en una sola lista para la UI
      let flatList: NewsArticle[] = []

      if (data.topics?.plone?.items) {
        flatList.push(...data.topics.plone.items.map((i: any) => ({ ...i, topic: "plone" })))
      }
      if (data.topics?.django?.items) {
        flatList.push(...data.topics.django.items.map((i: any) => ({ ...i, topic: "django" })))
      }
      if (data.topics?.ai?.sections) {
        data.topics.ai.sections.forEach((sec: any) => {
          flatList.push(...sec.items.map((i: any) => ({ ...i, topic: "ai" })))
        })
      }

      setArticles(flatList)
      if (flatList.length > 0) setSelectedArticle(flatList[0])
      setPdfTimestamp(Date.now())
    } catch (error) {
      console.error(error)
    } finally {
      setIsLoading(false)
    }
  }
  async function handleSendEmail() {
    setIsSending(true)
    try {
      const response = await fetch(`${API_URL}/api/bulletin/send`, { method: "POST" })
      if (!response.ok) throw new Error("Fallo al enviar el correo")

      alert("✅ ¡El boletín se ha enviado por correo correctamente!")
    } catch (error) {
      console.error(error)
      alert("❌ Hubo un error al enviar el correo.")
    } finally {
      setIsSending(false)
    }
  }
  function handleDiscard(id: number) {
    // Aquí luego meteremos la llamada a Python para recalcular
    const updated = articles.filter((a) => a.id !== id)
    setArticles(updated)
    if (selectedArticle?.id === id) setSelectedArticle(updated[0] ?? null)
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex h-14 items-center gap-3 border-b border-border bg-card px-8">
        <button onClick={() => onNavigate("home")} className="text-sm text-muted-foreground hover:text-foreground">Home</button>
        <span className="text-sm text-muted-foreground">/</span>
        <button onClick={() => onNavigate("module")} className="text-sm text-muted-foreground hover:text-foreground">News Bulletin</button>
        <span className="text-sm text-muted-foreground">/</span>
        <h1 className="text-sm font-medium text-foreground">Review Bulletin</h1>
      </header>

      <main className="flex-1 px-8 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">Review & Edit Bulletin</h2>
          <p className="mt-1 text-sm text-muted-foreground">Review the curated articles and approve the final PDF.</p>
        </div>

        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="size-8 animate-spin text-muted-foreground" />
          </div>
        ) : articles.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground">
            <FileText className="size-12 opacity-20" />
            <p className="text-base font-medium">No hay un boletín generado.</p>
            <p className="text-sm">Vuelve al dashboard y ejecuta la generación automática.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
            {/* IZQUIERDA - LISTA DE NOTICIAS */}
            <div className="lg:col-span-3">
              <Card className="border-border">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">Curated Articles</CardTitle>
                    <Badge variant="secondary" className="text-xs">{articles.length} articles</Badge>
                  </div>
                </CardHeader>
                <CardContent className="px-0 pb-0">
                  <ScrollArea className="h-[600px]">
                    <div className="flex flex-col">
                      {articles.map((article) => (
                        <div
                          key={article.id}
                          onClick={() => setSelectedArticle(article)}
                          className={cn(
                            "flex cursor-pointer flex-col gap-3 border-b border-border px-6 py-4 text-left transition-colors hover:bg-accent/50",
                            selectedArticle?.id === article.id && "bg-accent"
                          )}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex flex-1 flex-col gap-1.5">
                              <div className="flex items-center gap-2">
                                <Badge className={cn("text-[10px] font-semibold border-0 uppercase", topicColors[article.topic] ?? "")}>
                                  {article.topic}
                                </Badge>
                                <span className="text-xs font-bold text-muted-foreground">Nota: {article.llm_score}/10</span>
                              </div>
                              <h3 className="text-sm font-medium leading-snug text-foreground">{article.title}</h3>
                              <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">{article.summary_short}</p>
                            </div>
                            <div className="flex shrink-0 items-center gap-2">
                              <Button
                                variant="outline"
                                size="icon-sm"
                                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                                onClick={(e) => { e.stopPropagation(); handleDiscard(article.id); }}
                                title="Descartar y Regenerar"
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>

            {/* DERECHA - VISOR PDF Y BOTÓN DE ENVÍO */}
            <div className="flex flex-col gap-4 lg:col-span-2">
              <Card className="flex-1 border-border overflow-hidden">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">PDF Preview</CardTitle>
                </CardHeader>
                <CardContent className="p-0 h-[520px]">
                  {/* Visor de PDF embebido apuntando a tu FastAPI */}
                  <iframe
                    src={`${API_URL}/static/bulletin_compiled.pdf?t=${pdfTimestamp}#toolbar=0`}
                    className="w-full h-full border-0"
                    title="PDF Preview"
                  />
                </CardContent>
              </Card>

              <Button
                size="lg"
                className="h-12 bg-success text-success-foreground hover:bg-success/90"
                onClick={handleSendEmail}
                disabled={isSending}
              >
                {isSending ? (
                  <Loader2 className="size-5 mr-2 animate-spin" />
                ) : (
                  <>
                    <CheckCircle className="size-5 mr-2" />
                    <Mail className="size-5 mr-2" />
                  </>
                )}
                <span className="font-semibold">
                  {isSending ? "Sending Email..." : "Approve & Send Email"}
                </span>
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}