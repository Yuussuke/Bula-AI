"use client";

import { AlertCircle, ChevronDown, Mic, Send, Volume2 } from "lucide-react";
import { useState } from "react";

import { TypingIndicator } from "@/components/typing-indicator";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "ai";
  content: string;
  source?: string;
  rawText?: string;
  hasAlerts?: boolean;
}

export function LosartanaChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      role: "ai",
      content:
        "Olá! Sou o Bula AI, seu assistente especializado em Losartana Potássica. Estou aqui para ajudá-lo a entender tudo sobre este medicamento com base na bula oficial.",
      source: "Introdução - Bula Oficial",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: inputValue,
    };

    setMessages([...messages, userMessage]);
    setInputValue("");
    setIsTyping(true);

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
      };
      setMessages((prev) => [...prev, aiResponse]);
      setIsTyping(false);
    }, 2000);
  };

  const handleSpeak = (text: string) => {
    if ("speechSynthesis" in window) {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "pt-BR";
      speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Quick Summary Card - Only show when no user messages yet */}
      {messages.length === 1 && (
        <div className="px-4 pt-4 sm:px-6 sm:pt-6">
          <Card className="border-l-primary bg-primary/5 border-l-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm sm:text-base">
                Resumo Rápido - Losartana Potássica
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 sm:space-y-4">
              <div>
                <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                  Princípio Ativo
                </p>
                <p className="text-foreground mt-1 text-sm">Losartana Potássica 50mg</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                  Para que serve
                </p>
                <p className="text-foreground mt-1 text-sm">
                  Tratamento da pressão arterial elevada (hipertensão). Ajuda a reduzir o risco de
                  eventos cardiovasculares.
                </p>
              </div>
              <div className="border-primary/20 border-t pt-2">
                <div className="flex items-start gap-3">
                  <AlertCircle className="text-destructive mt-0.5 h-4 w-4 flex-shrink-0" />
                  <div>
                    <p className="text-destructive mb-2 text-xs font-semibold">
                      Alertas Críticos / Contraindicações
                    </p>
                    <ul className="text-foreground list-inside list-disc space-y-1 text-xs">
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
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:space-y-6 sm:px-6 sm:py-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn("flex gap-3 sm:gap-4", message.role === "user" && "justify-end")}
          >
            {message.role === "ai" ? (
              <>
                <div className="bg-primary/10 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full sm:h-8 sm:w-8">
                  <span className="text-primary text-[10px] font-semibold sm:text-xs">AI</span>
                </div>
                <div className="max-w-[85%] min-w-0 flex-1 space-y-2 sm:max-w-none">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-foreground text-sm font-medium">Bula AI</span>
                    {message.source && (
                      <Badge variant="outline" className="text-[10px] sm:text-xs">
                        Fonte: {message.source}
                      </Badge>
                    )}
                  </div>
                  <div className="bg-card border-border space-y-3 rounded-lg border p-3 sm:p-4">
                    <p className="text-foreground text-sm leading-relaxed">{message.content}</p>

                    {message.hasAlerts && (
                      <div className="border-l-2 border-amber-500 bg-amber-50/30 py-2 pl-3">
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
                            className="text-primary hover:text-primary/80 h-7 p-0 text-xs"
                          >
                            <ChevronDown className="mr-1 h-4 w-4" />
                            Ver trecho original da bula
                          </Button>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2">
                          <div className="bg-muted/30 border-muted rounded-md border-l-2 p-3">
                            <p className="text-muted-foreground text-xs leading-relaxed italic">
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
                        className="text-muted-foreground hover:text-primary h-7 gap-1 px-2"
                        title="Ouvir esta mensagem"
                      >
                        <Volume2 className="h-3.5 w-3.5" />
                        <span className="hidden text-[10px] sm:inline">Ouvir</span>
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
      <div className="border-border bg-card space-y-3 border-t px-4 py-4 sm:px-6">
        <div className="flex items-end gap-2 sm:gap-3">
          <Button
            variant="outline"
            size="icon"
            className="h-10 w-10 flex-shrink-0 sm:h-12 sm:w-12"
            title="Entrada de voz"
          >
            <Mic className="h-4 w-4 sm:h-5 sm:w-5" />
          </Button>
          <Input
            type="text"
            placeholder="Pergunte sobre Losartana..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
            className="h-10 text-sm sm:h-12"
          />
          <Button
            onClick={handleSendMessage}
            className="h-10 flex-shrink-0 gap-2 px-4 sm:h-12 sm:px-6"
            disabled={!inputValue.trim()}
          >
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">Enviar</span>
          </Button>
        </div>
        <p className="text-muted-foreground text-center text-xs">
          Dica: Pergunte sobre dosagem, contraindicações ou efeitos colaterais
        </p>
      </div>
    </div>
  );
}
