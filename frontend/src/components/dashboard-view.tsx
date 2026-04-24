"use client";

import {
  Check,
  CloudUpload,
  FileSearch,
  FileText,
  Loader2,
  LogOut,
  Menu,
  MessageCircle,
  MessageSquare,
  Mic,
  Pill,
  RefreshCw,
  Send,
  Trash2,
  Upload,
  Volume2,
  X,
} from "lucide-react";
import { useState } from "react";

import { LosartanaChat } from "@/components/losartana-chat";
import { MedicalWarning } from "@/components/medical-warning";
import { TypingIndicator } from "@/components/typing-indicator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

interface DashboardViewProps {
  onLogout: () => void;
}

type NavItem = "bulas" | "chat-general" | "chat-losartana";

interface Bula {
  id: string;
  medicationName: string;
  manufacturer: string;
  uploadDate: string;
  status: "processed" | "processing" | "error";
  chatRoute?: NavItem;
}

const mockBulas: Bula[] = [
  {
    id: "1",
    medicationName: "Paracetamol 500mg",
    manufacturer: "Laboratório X",
    uploadDate: "15/04/2026",
    status: "processed",
  },
  {
    id: "2",
    medicationName: "Ibuprofeno 400mg",
    manufacturer: "Laboratório Y",
    uploadDate: "14/04/2026",
    status: "processing",
  },
  {
    id: "3",
    medicationName: "Amoxicilina 875mg",
    manufacturer: "Laboratório W",
    uploadDate: "13/04/2026",
    status: "error",
  },
  {
    id: "4",
    medicationName: "Losartana Potássica 50mg",
    manufacturer: "Laboratório K",
    uploadDate: "12/04/2026",
    status: "processed",
    chatRoute: "chat-losartana",
  },
];

const statusConfig = {
  processed: {
    label: "Processado",
    variant: "default" as const,
    className: "bg-emerald-100 text-emerald-700 border-emerald-200",
    canChat: true,
  },
  processing: {
    label: "Processando",
    variant: "secondary" as const,
    className: "bg-amber-100 text-amber-700 border-amber-200",
    canChat: false,
  },
  error: {
    label: "Falha no Upload",
    variant: "destructive" as const,
    className: "bg-red-100 text-red-700 border-red-200",
    canChat: false,
  },
};

export function DashboardView({ onLogout }: DashboardViewProps) {
  const [activeNav, setActiveNav] = useState<NavItem>("bulas");
  const [bulas, setBulas] = useState<Bula[]>(mockBulas);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [medicationName, setMedicationName] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const handleDelete = (id: string) => {
    setBulas(bulas.filter((b) => b.id !== id));
  };

  const handleRetry = (id: string) => {
    setBulas(bulas.map((b) => (b.id === id ? { ...b, status: "processing" as const } : b)));
  };

  const handleFileSelect = () => {
    setSelectedFile("documento_selecionado.pdf");
  };

  const handleConfirmUpload = () => {
    if (!medicationName.trim()) {
      return;
    }

    const newBula: Bula = {
      id: String(Date.now()),
      medicationName: medicationName.trim(),
      manufacturer: manufacturer.trim() || "Não especificado",
      uploadDate: new Date().toLocaleDateString("pt-BR"),
      status: "processing",
    };
    setBulas([newBula, ...bulas]);
    setShowUploadModal(false);
    setMedicationName("");
    setManufacturer("");
    setSelectedFile(null);
  };

  const handleChatWithBula = (bula: Bula) => {
    if (bula.chatRoute) {
      setActiveNav(bula.chatRoute);
    } else {
      setActiveNav("chat-general");
    }
  };

  const handleNavClick = (nav: NavItem) => {
    setActiveNav(nav);
    setMobileMenuOpen(false);
  };

  const isChat = activeNav === "chat-general" || activeNav === "chat-losartana";

  const renderSidebarContent = () => (
    <>
      <div className="border-sidebar-border border-b p-6">
        <div className="flex items-center gap-3">
          <div className="bg-sidebar-primary/20 flex h-10 w-10 items-center justify-center rounded-xl">
            <Pill className="text-sidebar-primary h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold">Bula AI</h1>
            <p className="text-sidebar-foreground/60 text-xs">Healthcare Intelligence</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          <li>
            <button
              onClick={() => handleNavClick("bulas")}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-all",
                activeNav === "bulas"
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <FileText className="h-5 w-5" />
              Minhas Bulas
            </button>
          </li>

          <li className="pt-4">
            <div className="text-sidebar-foreground/50 px-4 py-2 text-xs font-semibold tracking-wide uppercase">
              Chats
            </div>
            <button
              onClick={() => handleNavClick("chat-general")}
              className={cn(
                "mt-2 flex w-full items-center gap-3 rounded-lg px-4 py-2 text-sm font-medium transition-all",
                activeNav === "chat-general"
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <MessageCircle className="h-5 w-5" />
              Chat AI (Geral)
            </button>
            <button
              onClick={() => handleNavClick("chat-losartana")}
              className={cn(
                "mt-1 flex w-full items-center gap-3 rounded-lg px-4 py-2 text-sm font-medium transition-all",
                activeNav === "chat-losartana"
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <MessageCircle className="h-5 w-5" />
              Losartana Potássica
            </button>
          </li>
        </ul>
      </nav>

      <div className="border-sidebar-border border-t p-4">
        <div className="bg-sidebar-accent/30 flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="bg-sidebar-primary/20 text-sidebar-primary flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium">
            JS
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">João Silva</p>
            <p className="text-sidebar-foreground/60 truncate text-xs">joao@email.com</p>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <div className="bg-background flex min-h-screen">
      {/* Desktop Sidebar */}
      <aside className="bg-sidebar text-sidebar-foreground border-sidebar-border hidden w-64 flex-col border-r md:flex">
        {renderSidebarContent()}
      </aside>

      {/* Mobile Sidebar (Sheet) */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="bg-sidebar text-sidebar-foreground w-72 p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Menu de navegação</SheetTitle>
          </SheetHeader>
          <div className="flex h-full flex-col">{renderSidebarContent()}</div>
        </SheetContent>
      </Sheet>

      {/* Main Content */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <header className="border-border bg-card flex h-14 items-center justify-between border-b px-4 sm:h-16 sm:px-6">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon-sm"
              className="md:hidden"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="h-5 w-5" />
              <span className="sr-only">Abrir menu</span>
            </Button>
            <div className="min-w-0">
              <h2 className="text-foreground truncate text-base font-semibold sm:text-lg">
                {activeNav === "bulas"
                  ? "Minhas Bulas"
                  : activeNav === "chat-general"
                    ? "Chat AI - Geral"
                    : "Chat AI - Losartana Potássica"}
              </h2>
              <p className="text-muted-foreground hidden text-xs sm:block sm:text-sm">
                {activeNav === "bulas"
                  ? "Gerencie suas bulas de medicamentos"
                  : "Converse com a IA sobre seus medicamentos"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <Avatar className="h-8 w-8 sm:h-9 sm:w-9">
              <AvatarImage src="" alt="User" />
              <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium sm:text-sm">
                JS
              </AvatarFallback>
            </Avatar>
            <Button variant="outline" size="sm" onClick={onLogout} className="hidden sm:flex">
              <LogOut className="mr-2 h-4 w-4" />
              Sair
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={onLogout} className="sm:hidden">
              <LogOut className="h-4 w-4" />
              <span className="sr-only">Sair</span>
            </Button>
          </div>
        </header>

        {/* Global Medical Warning for Chat Views */}
        {isChat && <MedicalWarning />}

        {/* Content Area */}
        <main className="flex-1 overflow-auto">
          {activeNav === "bulas" ? (
            <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
              {/* Header */}
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-foreground text-xl font-bold sm:text-2xl">Minhas Bulas</h3>
                  <p className="text-muted-foreground mt-1 text-sm">
                    {bulas.length} bulas carregadas
                  </p>
                </div>
                <Button
                  onClick={() => setShowUploadModal(true)}
                  size="default"
                  className="w-full gap-2 sm:w-auto"
                >
                  <Upload className="h-4 w-4" />
                  Adicionar nova bula
                </Button>
              </div>

              {/* Grid of Bula Cards OR Empty State */}
              {bulas.length > 0 ? (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6 lg:grid-cols-3">
                  {bulas.map((bula) => {
                    const config = statusConfig[bula.status];
                    const isError = bula.status === "error";

                    return (
                      <Card
                        key={bula.id}
                        className={cn(
                          "flex flex-col overflow-hidden transition-shadow",
                          isError
                            ? "border-red-200 bg-red-50/30 hover:shadow-md"
                            : "hover:shadow-lg"
                        )}
                      >
                        <CardHeader className="pb-3">
                          <CardTitle className="line-clamp-2 text-base sm:text-lg">
                            {bula.medicationName}
                          </CardTitle>
                          <CardDescription className="text-xs">{bula.manufacturer}</CardDescription>
                        </CardHeader>
                        <CardContent className="flex-1 space-y-3 pb-3">
                          <div className="text-muted-foreground text-sm">
                            <p className="text-muted-foreground/60 text-xs">Data de upload</p>
                            <p className="font-medium">{bula.uploadDate}</p>
                          </div>
                          <div>
                            <Badge
                              variant={config.variant}
                              className={cn("gap-1.5 text-xs", config.className)}
                            >
                              {bula.status === "processing" && (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              )}
                              {bula.status === "processed" && <Check className="h-3 w-3" />}
                              {config.label}
                            </Badge>
                          </div>
                        </CardContent>
                        <div className="border-border flex gap-2 border-t px-4 py-3 sm:px-6">
                          {isError ? (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-9 flex-1 gap-2 text-xs"
                              onClick={() => handleRetry(bula.id)}
                            >
                              <RefreshCw className="h-3.5 w-3.5" />
                              Tentar Novamente
                            </Button>
                          ) : (
                            <Button
                              variant="default"
                              size="sm"
                              className={cn(
                                "h-9 flex-1 gap-2 text-xs",
                                !config.canChat && "cursor-not-allowed opacity-50"
                              )}
                              disabled={!config.canChat}
                              onClick={() => handleChatWithBula(bula)}
                            >
                              <MessageSquare className="h-3.5 w-3.5" />
                              Conversar
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => handleDelete(bula.id)}
                            className="text-muted-foreground hover:text-destructive h-9 w-9"
                          >
                            <Trash2 className="h-4 w-4" />
                            <span className="sr-only">Excluir {bula.medicationName}</span>
                          </Button>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              ) : (
                /* Empty State */
                <Card className="border-2 border-dashed">
                  <CardContent className="flex flex-col items-center justify-center py-16 sm:py-24">
                    <div className="bg-muted/50 mb-6 flex h-20 w-20 items-center justify-center rounded-full sm:h-24 sm:w-24">
                      <FileSearch className="text-muted-foreground/50 h-10 w-10 sm:h-12 sm:w-12" />
                    </div>
                    <h3 className="text-foreground mb-2 text-center text-lg font-semibold sm:text-xl">
                      Nenhuma bula cadastrada ainda
                    </h3>
                    <p className="text-muted-foreground mb-6 max-w-sm text-center text-sm">
                      Comece enviando sua primeira bula de medicamento para conversar com a IA sobre
                      dosagens, efeitos e mais.
                    </p>
                    <Button
                      variant="secondary"
                      size="lg"
                      onClick={() => setShowUploadModal(true)}
                      className="gap-2"
                    >
                      <Upload className="h-4 w-4" />
                      Fazer upload da primeira bula
                    </Button>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : activeNav === "chat-losartana" ? (
            <LosartanaChat />
          ) : (
            <GeneralChat />
          )}
        </main>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="Fechar modal"
            className="bg-foreground/50 absolute inset-0 backdrop-blur-sm"
            onClick={() => {
              setShowUploadModal(false);
              setMedicationName("");
              setManufacturer("");
              setSelectedFile(null);
            }}
          />
          <Card className="relative z-10 w-full max-w-lg shadow-2xl">
            {/* Close button - absolute top-right */}
            <Button
              variant="ghost"
              size="icon-sm"
              className="absolute top-3 right-3 z-10"
              onClick={() => {
                setShowUploadModal(false);
                setMedicationName("");
                setManufacturer("");
                setSelectedFile(null);
              }}
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Fechar</span>
            </Button>
            <CardHeader className="pr-12">
              <CardTitle className="text-lg">Adicionar nova bula</CardTitle>
              <CardDescription>Preencha as informações e envie o PDF</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label
                  htmlFor="medication-name"
                  className="text-foreground mb-2 block text-sm font-medium"
                >
                  Nome do medicamento <span className="text-destructive">*</span>
                </label>
                <Input
                  id="medication-name"
                  type="text"
                  placeholder="Ex: Losartana Potássica 50mg"
                  value={medicationName}
                  onChange={(e) => setMedicationName(e.target.value)}
                  className="text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="manufacturer"
                  className="text-foreground mb-2 block text-sm font-medium"
                >
                  Fabricante
                </label>
                <Input
                  id="manufacturer"
                  type="text"
                  placeholder="Ex: Laboratório X"
                  value={manufacturer}
                  onChange={(e) => setManufacturer(e.target.value)}
                  className="text-sm"
                />
              </div>
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragOver(false);
                  handleFileSelect();
                }}
                className={cn(
                  "cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-all sm:p-8",
                  isDragOver
                    ? "border-primary bg-primary/5"
                    : selectedFile
                      ? "border-primary/50 bg-primary/5"
                      : "border-border hover:border-primary/50 hover:bg-muted/50"
                )}
              >
                {selectedFile ? (
                  <>
                    <div className="bg-primary/20 mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full sm:h-12 sm:w-12">
                      <Check className="text-primary h-5 w-5 sm:h-6 sm:w-6" />
                    </div>
                    <h3 className="text-foreground mb-1 text-sm font-medium">
                      Arquivo selecionado
                    </h3>
                    <p className="text-primary text-xs font-medium">{selectedFile}</p>
                    <p className="text-muted-foreground mt-2 text-xs">
                      Clique para trocar o arquivo
                    </p>
                  </>
                ) : (
                  <>
                    <div className="bg-primary/10 mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full sm:h-12 sm:w-12">
                      <CloudUpload className="text-primary h-5 w-5 sm:h-6 sm:w-6" />
                    </div>
                    <h3 className="text-foreground mb-1 text-sm font-medium">
                      Arraste e solte seu arquivo
                    </h3>
                    <p className="text-muted-foreground mb-2 text-xs">ou clique para selecionar</p>
                    <p className="text-muted-foreground text-xs">PDF até 10MB</p>
                  </>
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={handleFileSelect}
                >
                  Selecionar arquivo
                </Button>
              </div>

              {/* Confirm Upload Button */}
              <Button
                onClick={handleConfirmUpload}
                className="w-full"
                size="lg"
                disabled={!medicationName.trim() || !selectedFile}
              >
                <Upload className="mr-2 h-4 w-4" />
                Confirmar Envio
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// General Chat Component
function GeneralChat() {
  const [inputValue, setInputValue] = useState("");
  const [isTyping] = useState(true);

  const handleSpeak = (text: string) => {
    if ("speechSynthesis" in window) {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "pt-BR";
      speechSynthesis.speak(utterance);
    }
  };

  const welcomeMessage = "Olá! Sou o Bula AI, seu assistente de saúde. Como posso ajudá-lo hoje?";

  return (
    <div className="flex h-full flex-col">
      {/* Chat Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:space-y-6 sm:p-6">
        {/* AI Welcome Message */}
        <div className="flex gap-3 sm:gap-4">
          <div className="bg-primary/10 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full sm:h-8 sm:w-8">
            <span className="text-primary text-[10px] font-semibold sm:text-xs">AI</span>
          </div>
          <div className="max-w-[85%] min-w-0 flex-1 space-y-2 sm:max-w-none">
            <span className="text-foreground text-sm font-medium">Bula AI</span>
            <div className="bg-card border-border space-y-3 rounded-lg border p-3 sm:p-4">
              <p className="text-foreground text-sm leading-relaxed">{welcomeMessage}</p>
              <div className="flex justify-end pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSpeak(welcomeMessage)}
                  className="text-muted-foreground hover:text-primary h-7 gap-1 px-2"
                  title="Ouvir esta mensagem"
                >
                  <Volume2 className="h-3.5 w-3.5" />
                  <span className="hidden text-[10px] sm:inline">Ouvir</span>
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Typing Indicator (Demo) */}
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
            placeholder="Digite sua pergunta..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="h-10 text-sm sm:h-12"
          />
          <Button
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
