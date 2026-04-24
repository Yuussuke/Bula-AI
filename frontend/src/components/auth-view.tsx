"use client";

import { useMutation } from "@tanstack/react-query";
import { Pill, Shield, Sparkles } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { loginRequest, registerRequest } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export function AuthView() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [registerFullName, setRegisterFullName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [loginErrorMessage, setLoginErrorMessage] = useState<string | null>(null);
  const [registerErrorMessage, setRegisterErrorMessage] = useState<string | null>(null);

  const loginMutation = useMutation({
    mutationFn: loginRequest,
    onSuccess: (payload) => {
      setAuth({
        accessToken: payload.token.access_token,
        user: payload.user,
      });
      void navigate("/", { replace: true });
    },
    onError: (error: Error) => {
      setLoginErrorMessage(error.message);
    },
  });

  const registerMutation = useMutation({
    mutationFn: registerRequest,
    onSuccess: (payload) => {
      setAuth({
        accessToken: payload.token.access_token,
        user: payload.user,
      });
      void navigate("/", { replace: true });
    },
    onError: (error: Error) => {
      setRegisterErrorMessage(error.message);
    },
  });

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoginErrorMessage(null);
    loginMutation.mutate({
      email: loginEmail,
      password: loginPassword,
    });
  };

  const handleRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setRegisterErrorMessage(null);
    registerMutation.mutate({
      email: registerEmail,
      full_name: registerFullName,
      password: registerPassword,
    });
  };

  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="bg-primary/5 absolute top-1/4 -left-20 h-72 w-72 rounded-full blur-3xl" />
        <div className="bg-accent/5 absolute -right-20 bottom-1/4 h-96 w-96 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="bg-primary/10 mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl">
            <Pill className="text-primary h-8 w-8" />
          </div>
          <h1 className="text-foreground text-3xl font-bold tracking-tight">Bula AI</h1>
          <p className="text-muted-foreground mt-2">
            Inteligência artificial para bulas de medicamentos
          </p>
        </div>

        <Card className="border-border/50 shadow-primary/5 shadow-xl">
          <CardHeader className="pb-2 text-center">
            <CardTitle className="text-xl">Bem-vindo</CardTitle>
            <CardDescription>Acesse sua conta ou crie uma nova</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="mb-6 grid w-full grid-cols-2">
                <TabsTrigger value="login">Entrar</TabsTrigger>
                <TabsTrigger value="register">Cadastrar</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={handleLoginSubmit}>
                  <FieldGroup>
                    <Field>
                      <FieldLabel htmlFor="email">E-mail</FieldLabel>
                      <Input
                        id="email"
                        type="email"
                        placeholder="seu@email.com"
                        value={loginEmail}
                        onChange={(event) => setLoginEmail(event.target.value)}
                        required
                      />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="password">Senha</FieldLabel>
                      <Input
                        id="password"
                        type="password"
                        placeholder="••••••••"
                        value={loginPassword}
                        onChange={(event) => setLoginPassword(event.target.value)}
                        required
                      />
                    </Field>
                  </FieldGroup>
                  {loginErrorMessage ? (
                    <p className="text-destructive mt-3 text-sm" role="alert">
                      {loginErrorMessage}
                    </p>
                  ) : null}
                  <Button type="submit" className="mt-6 w-full" disabled={loginMutation.isPending}>
                    {loginMutation.isPending ? "Entrando..." : "Entrar"}
                  </Button>
                  <p className="text-muted-foreground mt-4 text-center text-sm">
                    <button type="button" className="text-primary hover:underline">
                      Esqueceu sua senha?
                    </button>
                  </p>
                </form>
              </TabsContent>

              <TabsContent value="register">
                <form onSubmit={handleRegisterSubmit}>
                  <FieldGroup>
                    <Field>
                      <FieldLabel htmlFor="fullName">Nome completo</FieldLabel>
                      <Input
                        id="fullName"
                        type="text"
                        placeholder="João Silva"
                        value={registerFullName}
                        onChange={(event) => setRegisterFullName(event.target.value)}
                        required
                      />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="registerEmail">E-mail</FieldLabel>
                      <Input
                        id="registerEmail"
                        type="email"
                        placeholder="seu@email.com"
                        value={registerEmail}
                        onChange={(event) => setRegisterEmail(event.target.value)}
                        required
                      />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="registerPassword">Senha</FieldLabel>
                      <Input
                        id="registerPassword"
                        type="password"
                        placeholder="••••••••"
                        value={registerPassword}
                        onChange={(event) => setRegisterPassword(event.target.value)}
                        required
                      />
                    </Field>
                  </FieldGroup>
                  {registerErrorMessage ? (
                    <p className="text-destructive mt-3 text-sm" role="alert">
                      {registerErrorMessage}
                    </p>
                  ) : null}
                  <Button
                    type="submit"
                    className="mt-6 w-full"
                    disabled={registerMutation.isPending}
                  >
                    {registerMutation.isPending ? "Criando conta..." : "Criar conta"}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <div className="text-muted-foreground mt-8 grid grid-cols-2 gap-4 text-center text-sm">
          <div className="bg-card/50 flex flex-col items-center gap-2 rounded-lg p-4">
            <Shield className="text-primary h-5 w-5" />
            <span>Dados seguros e protegidos</span>
          </div>
          <div className="bg-card/50 flex flex-col items-center gap-2 rounded-lg p-4">
            <Sparkles className="text-accent h-5 w-5" />
            <span>IA de última geração</span>
          </div>
        </div>
      </div>
    </div>
  );
}
