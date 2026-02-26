"use client"

import { useState } from "react"
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Trash2, FileText, Mail, CheckCircle } from "lucide-react"
import { cn } from "@/lib/utils"

type View = "home" | "module" | "add-news" | "review"

interface NewsArticle {
  id: number
  title: string
  topic: string
  summary: string
  score: number
}

const initialArticles: NewsArticle[] = [
  {
    id: 1,
    title: "Plone 6.1 Released with Volto Improvements",
    topic: "Plone",
    summary:
      "The latest Plone release brings significant improvements to the Volto frontend, including faster rendering, better accessibility, and new content editing blocks.",
    score: 9.2,
  },
  {
    id: 2,
    title: "Django 5.2 Introduces Composite Primary Keys",
    topic: "Django",
    summary:
      "Django 5.2 adds native support for composite primary keys, a long-awaited feature that simplifies working with legacy databases and complex schemas.",
    score: 8.7,
  },
  {
    id: 3,
    title: "OpenAI Releases GPT-5 with Multimodal Reasoning",
    topic: "AI",
    summary:
      "GPT-5 demonstrates a leap in reasoning capabilities with native multimodal understanding, enabling seamless integration of text, image, and audio inputs.",
    score: 8.5,
  },
  {
    id: 4,
    title: "Building REST APIs with Django Ninja 2.0",
    topic: "Django",
    summary:
      "Django Ninja 2.0 introduces async-first API building with improved schema validation and auto-generated documentation capabilities.",
    score: 7.8,
  },
  {
    id: 5,
    title: "AI-Powered Code Review Tools Gain Traction",
    topic: "AI",
    summary:
      "New AI-powered code review assistants are reducing review times by up to 40%, with tools like CodeRabbit and Ellipsis leading the market adoption.",
    score: 7.4,
  },
]

interface ReviewViewProps {
  onNavigate: (view: View) => void
}

const topicColors: Record<string, string> = {
  Plone: "bg-[oklch(0.55_0.15_220)] text-[oklch(0.985_0_0)]",
  Django: "bg-[oklch(0.52_0.17_152)] text-[oklch(0.985_0_0)]",
  AI: "bg-[oklch(0.55_0.2_280)] text-[oklch(0.985_0_0)]",
}

export function ReviewView({ onNavigate }: ReviewViewProps) {
  const [articles, setArticles] = useState(initialArticles)
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(
    articles[0] ?? null
  )

  function handleDiscard(id: number) {
    const updated = articles.filter((a) => a.id !== id)
    setArticles(updated)
    if (selectedArticle?.id === id) {
      setSelectedArticle(updated[0] ?? null)
    }
  }

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
        <button
          onClick={() => onNavigate("module")}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          News Bulletin
        </button>
        <span className="text-sm text-muted-foreground">/</span>
        <h1 className="text-sm font-medium text-foreground">
          Review Bulletin
        </h1>
      </header>

      <main className="flex-1 px-8 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Review & Edit Bulletin
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Review the curated articles, discard irrelevant ones, and approve the final bulletin.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          {/* Left Column - News List */}
          <div className="lg:col-span-3">
            <Card className="border-border">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">
                    Curated Articles
                  </CardTitle>
                  <Badge variant="secondary" className="text-xs">
                    {articles.length} articles
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="px-0 pb-0">
                <ScrollArea className="h-[520px]">
                  <div className="flex flex-col">
                    {articles.map((article) => (
                      <div
                        key={article.id}
                        role="button"
                        tabIndex={0}
                        onClick={() => setSelectedArticle(article)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault()
                            setSelectedArticle(article)
                          }
                        }}
                        className={cn(
                          "flex cursor-pointer flex-col gap-3 border-b border-border px-6 py-4 text-left transition-colors hover:bg-accent/50",
                          selectedArticle?.id === article.id && "bg-accent"
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex flex-1 flex-col gap-1.5">
                            <div className="flex items-center gap-2">
                              <Badge
                                className={cn(
                                  "text-[10px] font-semibold border-0",
                                  topicColors[article.topic] ?? ""
                                )}
                              >
                                {article.topic}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                Score: {article.score}/10
                              </span>
                            </div>
                            <h3 className="text-sm font-medium leading-snug text-foreground">
                              {article.title}
                            </h3>
                            <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
                              {article.summary}
                            </p>
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            <div className="flex size-10 items-center justify-center rounded-md bg-muted text-xs font-bold text-foreground">
                              {article.score}
                            </div>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDiscard(article.id)
                              }}
                              aria-label={`Discard ${article.title}`}
                            >
                              <Trash2 className="size-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                    {articles.length === 0 && (
                      <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground">
                        <FileText className="size-8" />
                        <p className="text-sm">No articles remaining</p>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Preview & Action */}
          <div className="flex flex-col gap-4 lg:col-span-2">
            <Card className="flex-1 border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">
                  PDF Preview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex h-[360px] flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/50">
                  <FileText className="mb-3 size-10 text-muted-foreground/50" />
                  <p className="text-sm font-medium text-muted-foreground">
                    PDF Preview loaded here
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground/70">
                    {selectedArticle
                      ? `Previewing: ${selectedArticle.title}`
                      : "Select an article to preview"}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Button
              size="lg"
              className="h-12 bg-success text-success-foreground hover:bg-success/90"
              disabled={articles.length === 0}
            >
              <CheckCircle className="size-5" />
              <Mail className="size-5" />
              <span className="font-semibold">Approve & Send Email</span>
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
