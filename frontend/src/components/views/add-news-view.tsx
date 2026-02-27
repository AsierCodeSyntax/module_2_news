"use client"

import { useState } from "react"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Link, Loader2 } from "lucide-react"

type View = "home" | "module" | "add-news" | "review"

interface AddNewsViewProps {
  onNavigate: (view: View) => void
}

export function AddNewsView({ onNavigate }: AddNewsViewProps) {
  const [url, setUrl] = useState("")
  const [topic, setTopic] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setIsLoading(true)

    try {
      // Usamos la variable de entorno que pusimos en Docker, o localhost por defecto
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

      const response = await fetch(`${API_URL}/api/news/manual`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url,
          topic: topic
        }),
      })

      if (!response.ok) {
        throw new Error("Fallo al enviar la noticia a la API")
      }

      setSubmitted(true)
      setUrl("")
      setTopic("")
      setTimeout(() => setSubmitted(false), 3000)

    } catch (error) {
      console.error("Error:", error)
      alert("Hubo un error al conectar con el servidor.")
    } finally {
      setIsLoading(false)
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
        <h1 className="text-sm font-medium text-foreground">Add Manual News</h1>
      </header>

      <main className="flex-1 px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            Add Manual News
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Submit an article URL to be ingested and evaluated for the bulletin.
          </p>
        </div>

        <Card className="max-w-lg border-border">
          <CardHeader>
            <CardTitle className="text-base">Submit Article</CardTitle>
            <CardDescription>
              Provide the article URL and select a topic to begin evaluation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <Label htmlFor="url" className="text-sm font-medium text-foreground">
                  Article URL
                </Label>
                <div className="relative">
                  <Link className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="url"
                    type="url"
                    placeholder="https://example.com/article"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="pl-9"
                    required
                  />
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="topic" className="text-sm font-medium text-foreground">
                  Topic
                </Label>
                <Select value={topic} onValueChange={setTopic} required>
                  <SelectTrigger className="w-full" id="topic">
                    <SelectValue placeholder="Select a topic" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="plone">Plone</SelectItem>
                    <SelectItem value="django">Django</SelectItem>
                    <SelectItem value="ai">AI</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                type="submit"
                disabled={!url || !topic || isLoading}
                className="w-full"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Processing...
                  </>
                ) : submitted ? (
                  "Submitted successfully"
                ) : (
                  "Ingest & Evaluate"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
