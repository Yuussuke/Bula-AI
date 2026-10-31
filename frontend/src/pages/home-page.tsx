import { ArrowUpRight, BookOpenText, LockKeyhole, MessageSquareText } from "lucide-react";
import type { ReactElement } from "react";
import { Link } from "react-router-dom";

import { useAuthStore } from "@/store/auth";

const destinations = [
  {
    path: "/minhas-bulas",
    title: "Minhas bulas",
    description:
      "Seus PDFs em um só lugar. Envie documentos, acompanhe o processamento e consulte suas bulas em particular.",
    action: "Abrir meu espaço",
    icon: LockKeyhole,
    style: "bg-sky-50 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300",
  },
  {
    path: "/catalogo",
    title: "Catálogo Geral",
    description:
      "Consulte bulas da ANVISA e compartilhadas após curadoria. Escolha as fontes antes de conversar.",
    action: "Explorar catálogo",
    icon: BookOpenText,
    style: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300",
  },
  {
    path: "/chat",
    title: "Chat geral",
    description:
      "Faça uma pergunta sobre medicamentos disponíveis no catálogo e consulte as fontes usadas na resposta.",
    action: "Iniciar conversa",
    icon: MessageSquareText,
    style: "bg-violet-50 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300",
  },
];

export function HomePage(): ReactElement {
  const firstName = useAuthStore((state) => state.user?.name.trim().split(/\s+/)[0]);
  return (
    <section className="space-y-8 py-3 sm:py-8" aria-labelledby="home-title">
      <div className="max-w-2xl space-y-3">
        <p className="text-primary text-sm font-medium">Seu espaço de consulta</p>
        <h1 id="home-title" className="text-3xl font-semibold tracking-tight sm:text-4xl">
          {firstName ? `Olá, ${firstName}.` : "Olá."} Como podemos ajudar?
        </h1>
        <p className="text-muted-foreground leading-relaxed">
          Escolha entre seus documentos, o catálogo de bulas e uma conversa com o assistente.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {destinations.map(({ path, title, description, action, icon: Icon, style }) => (
          <Link
            key={path}
            to={path}
            className="bg-card hover:border-primary/50 focus-visible:ring-primary group flex flex-col rounded-2xl border p-6 transition-shadow hover:shadow-md focus-visible:ring-2 focus-visible:outline-none"
          >
            <span className={`mb-6 w-fit rounded-xl p-3 ${style}`}>
              <Icon aria-hidden="true" className="h-6 w-6" />
            </span>
            <h2 className="text-xl font-semibold">{title}</h2>
            <p className="text-muted-foreground mt-3 flex-1 text-sm leading-relaxed">
              {description}
            </p>
            <span className="text-primary mt-7 flex items-center justify-between text-sm font-medium">
              {action}
              <ArrowUpRight
                aria-hidden="true"
                className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              />
            </span>
          </Link>
        ))}
      </div>
      <p className="text-muted-foreground max-w-3xl text-sm leading-relaxed">
        O Bula AI ajuda a consultar informações das bulas. Ele não substitui a orientação de um
        profissional de saúde nem decide tratamentos individuais.
      </p>
    </section>
  );
}
