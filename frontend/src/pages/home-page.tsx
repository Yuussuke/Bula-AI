import { ArrowRight, BookOpenText, FolderOpen } from "lucide-react";
import type { ReactElement } from "react";
import { Link } from "react-router-dom";

import { AssistantAvatar } from "@/components/assistant-avatar";
import { HomeConversations } from "@/components/chat/home-conversations";
import { AnimatedIcon } from "@/components/ui/animated-icon";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";

const destinations = [
  {
    path: "/catalogo",
    title: "Catálogo Geral",
    description: "Encontre um medicamento",
    icon: BookOpenText,
  },
  {
    path: "/minhas-bulas",
    title: "Minhas bulas",
    description: "Consulte seus PDFs",
    icon: FolderOpen,
  },
];

export function HomePage(): ReactElement {
  const firstName = useAuthStore((state) => state.user?.name.trim().split(/\s+/)[0]);
  return (
    <section className="min-h-[calc(100dvh-6rem)] py-4 sm:py-8" aria-labelledby="home-title">
      <div className="mb-8 space-y-3 sm:mb-10">
        <h1 id="home-title" className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {firstName ? `Olá, ${firstName}.` : "Olá."}
        </h1>
        <p className="text-muted-foreground max-w-3xl text-sm leading-relaxed sm:text-base">
          Consulte informações das bulas de medicamentos e confira as fontes das respostas.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.7fr_1fr]">
        <article
          aria-labelledby="home-chat-title"
          className="home-enter home-enter-left border-primary/15 bg-secondary/55 dark:bg-card/60 relative flex min-w-0 items-center justify-between gap-3 rounded-2xl border p-6 backdrop-blur-[2px] sm:gap-6 sm:p-8"
          style={{ animationDelay: "60ms" }}
        >
          <div className="relative z-10 max-w-sm min-w-0">
            <h2 id="home-chat-title" className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Chat geral
            </h2>
            <p className="text-muted-foreground mt-3 text-sm leading-relaxed sm:text-base">
              Tire dúvidas sobre os medicamentos disponíveis no catálogo.
            </p>
            <Button asChild size="lg" className="mt-6 gap-3 rounded-xl">
              <Link to="/chat">
                Iniciar conversa
                <AnimatedIcon icon={ArrowRight} effect="send" />
              </Link>
            </Button>
          </div>
          <AssistantAvatar className="h-24 w-24 sm:h-36 sm:w-36 xl:h-44 xl:w-44" />
        </article>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          {destinations.map(({ path, title, description, icon: Icon }, index) => (
            <Link
              key={path}
              to={path}
              className="home-enter home-enter-right border-border/70 bg-card/55 hover:border-primary/35 focus-visible:ring-primary flex min-w-0 items-center gap-4 rounded-2xl border p-5 backdrop-blur-[2px] transition-[border-color,box-shadow] duration-200 hover:shadow-sm focus-visible:ring-2 focus-visible:outline-none sm:p-6"
              style={{ animationDelay: `${140 + index * 100}ms` }}
            >
              <AnimatedIcon icon={Icon} className="text-primary h-7 w-7" />
              <div className="min-w-0 flex-1">
                <h2 className="text-base font-semibold sm:text-lg">{title}</h2>
                <span className="text-muted-foreground mt-1 block text-sm">{description}</span>
              </div>
              <AnimatedIcon icon={ArrowRight} effect="send" className="text-primary" />
            </Link>
          ))}
        </div>
      </div>

      <div className="mt-8 sm:mt-10">
        <HomeConversations />
      </div>

      <p className="text-muted-foreground mt-10 max-w-3xl text-xs leading-relaxed sm:mt-12 sm:text-sm">
        O Bula AI não substitui a orientação de um profissional de saúde.
      </p>
    </section>
  );
}
