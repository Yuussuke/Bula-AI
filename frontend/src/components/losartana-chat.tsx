"use client"

import { useState } from "react"
import {
  Send,
  Volume2,
  AlertCircle,
  ChevronDown,
  Mic,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible"
import { TypingIndicator } from "@/components/typing-indicator"
import { cn } from "@/lib/utils"

interface ChatMessage {
  id: string
  role: "user" | "ai"
  content: string
  source?: string
  rawText?: string
  hasAlerts?: boolean
}

export function LosartanaChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      role: "ai",
      content: "Olá! Sou o Bula AI, seu assistente especializado em Losartana Potássica. Estou aqui para ajudá-lo a entender tudo sobre este medicamento com base na bula oficial.",
      source: "Introdução - Bula Oficial",
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)

  const handleSendMessage = () => {
    if (!inputValue.trim()) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: inputValue,
    }

    setMessages([...messages, userMessage])
    setInputValue("")
    setIsTyping(true)

    // Simulate AI response
    setTimeout(() => {
      const aiResponse: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: "ai",
        content:
          "A Losartana Potássica é um medicamento utilizado no tratamento da hipertensão arterial. Ela atua bloqueando receptores de angiotensina II, ajudando a relaxar os vasos sanguíneos e reduzir a pressão arterial.",
        source: "Seção 1 - O que é Losartana Potássica",
        rawText:
          "Losartana potássica é um antagonista de receptor de angiotensina II (BRA). Seu principal mecanismo de ação é a redução da pressão arterial sistêmica através do bloqueio seletivo do receptor AT1 de angiotensina II.",
        hasAlerts: false,
      }
      setMessages(prev => [...prev, aiResponse])
      setIsTyping(false)
    }, 2000)
  }

  const handleSpeak = (text: string) => {
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'pt-BR'
      speechSynthesis.speak(utterance)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Quick Summary Card - Only show when no user messages yet */}
      {messages.length === 1 && (
        <div className="px-4 sm:px-6 pt-4 sm:pt-6">
          <Card className="border-l-4 border-l-primary bg-primary/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm sm:text-base">Resumo Rápido - Losartana Potássica</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 sm:space-y-4">
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Princípio Ativo
                </p>
                <p className="text-sm text-foreground mt-1">Losartana Potássica 50mg</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Para que serve
                </p>
                <p className="text-sm text-foreground mt-1">
                  Tratamento da pressão arterial elevada (hipertensão). Ajuda a reduzir o risco de eventos cardiovasculares.
                </p>
              </div>
              <div className="pt-2 border-t border-primary/20">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-semibold text-destructive mb-2">
                      Alertas Críticos / Contraindicações
                    </p>
                    <ul className="text-xs text-foreground space-y-1 list-disc list-inside">
                      <li>Evitar em gravidez (especialmente 2º e 3º trimestre)</li>
                      <li>Cuidado com insuficiência renal grave</li>
                      <li>Não usar se alérgico a qualquer componente</li>
                    </ul>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6">
        {messages.map((message) => (
          <div key={message.id} className={cn("flex gap-3 sm:gap-4", message.role === "user" && "justify-end")}>
            {message.role === "ai" ? (
              <>
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <span className="text-[10px] sm:text-xs font-semibold text-primary">AI</span>
                </div>
                <div className="flex-1 space-y-2 min-w-0 max-w-[85%] sm:max-w-none">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-foreground">Bula AI</span>
                    {message.source && (
                      <Badge variant="outline" className="text-[10px] sm:text-xs">
                        Fonte: {message.source}
                      </Badge>
                    )}
                  </div>
                  <div className="bg-card border border-border rounded-lg p-3 sm:p-4 space-y-3">
                    <p className="text-sm text-foreground leading-relaxed">{message.content}</p>

                    {message.hasAlerts && (
                      <div className="pl-3 border-l-2 border-amber-500 bg-amber-50/30 py-2">
                        <p className="text-xs font-semibold text-amber-700">
                          Alerta: Possíveis efeitos colaterais mencionados
                        </p>
                      </div>
                    )}

                    {message.rawText && (
                      <Collapsible>
                        <CollapsibleTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-xs text-primary hover:text-primary/80 h-7 p-0"
                          >
                            <ChevronDown className="w-4 h-4 mr-1" />
                            Ver trecho original da bula
                          </Button>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2">
                          <div className="bg-muted/30 rounded-md p-3 border-l-2 border-muted">
                            <p className="text-xs text-muted-foreground italic leading-relaxed">
                              {message.rawText}
                            </p>
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    )}

                    {/* Per-message speaker button */}
                    <div className="flex justify-end pt-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSpeak(message.content)}
                        className="text-muted-foreground hover:text-primary h-7 px-2 gap-1"
                        title="Ouvir esta mensagem"
                      >
                        <Volume2 className="w-3.5 h-3.5" />
                        <span className="text-[10px] hidden sm:inline">Ouvir</span>
                      </Button>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="max-w-[85%] sm:max-w-xs">
                <div className="bg-primary text-primary-foreground rounded-lg p-3 sm:p-4">
                  <p className="text-sm leading-relaxed">{message.content}</p>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Typing Indicator */}
        {isTyping && <TypingIndicator />}
      </div>

      {/* Input Area */}
      <div className="border-t border-border px-4 sm:px-6 py-4 bg-card space-y-3">
        <div className="flex gap-2 sm:gap-3 items-end">
          <Button
            variant="outline"
            size="icon"
            className="h-10 w-10 sm:h-12 sm:w-12 flex-shrink-0"
            title="Entrada de voz"
          >
            <Mic className="w-4 h-4 sm:w-5 sm:h-5" />
          </Button>
          <Input
            type="text"
            placeholder="Pergunte sobre Losartana..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
            className="h-10 sm:h-12 text-sm"
          />
          <Button
            onClick={handleSendMessage}
            className="h-10 sm:h-12 px-4 sm:px-6 flex-shrink-0 gap-2"
            disabled={!inputValue.trim()}
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline">Enviar</span>
          </Button>
        </div>
        <p className="text-xs text-muted-foreground text-center">
          Dica: Pergunte sobre dosagem, contraindicações ou efeitos colaterais
        </p>
      </div>
    </div>
  )
}
