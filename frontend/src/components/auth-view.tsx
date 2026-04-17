"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { FieldGroup, Field, FieldLabel } from "@/components/ui/field"
import { Pill, Shield, Sparkles } from "lucide-react"

interface AuthViewProps {
  onLogin: () => void
}

export function AuthView({ onLogin }: AuthViewProps) {
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setTimeout(() => {
      setIsLoading(false)
      onLogin()
    }, 1000)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-72 h-72 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-4">
            <Pill className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">Bula AI</h1>
          <p className="text-muted-foreground mt-2">Inteligência artificial para bulas de medicamentos</p>
        </div>

        <Card className="border-border/50 shadow-xl shadow-primary/5">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl">Bem-vindo</CardTitle>
            <CardDescription>Acesse sua conta ou crie uma nova</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="login">Entrar</TabsTrigger>
                <TabsTrigger value="register">Cadastrar</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={handleSubmit}>
                  <FieldGroup>
                    <Field>
                      <FieldLabel htmlFor="email">E-mail</FieldLabel>
                      <Input
                        id="email"
                        type="email"
                        placeholder="seu@email.com"
                        required
                      />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="password">Senha</FieldLabel>
                      <Input
                        id="password"
                        type="password"
                        placeholder="••••••••"
                        required
                      />
                    </Field>
                  </FieldGroup>
                  <Button 
                    type="submit" 
                    className="w-full mt-6" 
                    disabled={isLoading}
                  >
                    {isLoading ? "Entrando..." : "Entrar"}
                  </Button>
                  <p className="text-center text-sm text-muted-foreground mt-4">
                    <a href="#" className="text-primary hover:underline">Esqueceu sua senha?</a>
                  </p>
                </form>
              </TabsContent>

              <TabsContent value="register">
                <form onSubmit={handleSubmit}>
                  <FieldGroup>
                    <Field>
                      <FieldLabel htmlFor="fullName">Nome completo</FieldLabel>
                      <Input
                        id="fullName"
                        type="text"
                        placeholder="João Silva"
                        required
                      />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="registerEmail">E-mail</FieldLabel>
                      <Input
                        id="registerEmail"
                        type="email"
                        placeholder="seu@email.com"
                        required
                      />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="registerPassword">Senha</FieldLabel>
                      <Input
                        id="registerPassword"
                        type="password"
                        placeholder="••••••••"
                        required
                      />
                    </Field>
                  </FieldGroup>
                  <Button 
                    type="submit" 
                    className="w-full mt-6" 
                    disabled={isLoading}
                  >
                    {isLoading ? "Criando conta..." : "Criar conta"}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <div className="mt-8 grid grid-cols-2 gap-4 text-center text-sm text-muted-foreground">
          <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-card/50">
            <Shield className="w-5 h-5 text-primary" />
            <span>Dados seguros e protegidos</span>
          </div>
          <div className="flex flex-col items-center gap-2 p-4 rounded-lg bg-card/50">
            <Sparkles className="w-5 h-5 text-accent" />
            <span>IA de última geração</span>
          </div>
        </div>
      </div>
    </div>
  )
}
