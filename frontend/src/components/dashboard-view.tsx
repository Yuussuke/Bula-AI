"use client"

import { useState } from "react"
import { 
  FileText, 
  MessageSquare, 
  Upload, 
  Trash2, 
  LogOut, 
  Pill,
  X,
  CloudUpload,
  Check,
  Loader2,
  MessageCircle,
  Send,
  Menu,
  Mic,
  Volume2,
  RefreshCw,
  FileSearch
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { MedicalWarning } from "@/components/medical-warning"
import { LosartanaChat } from "@/components/losartana-chat"
import { TypingIndicator } from "@/components/typing-indicator"
import { cn } from "@/lib/utils"

interface DashboardViewProps {
  onLogout: () => void
}

type NavItem = "bulas" | "chat-general" | "chat-losartana"

interface Bula {
  id: string
  medicationName: string
  manufacturer: string
  uploadDate: string
  status: "processed" | "processing" | "error"
  chatRoute?: NavItem
}

const mockBulas: Bula[] = [
  { id: "1", medicationName: "Paracetamol 500mg", manufacturer: "Laboratório X", uploadDate: "15/04/2026", status: "processed" },
  { id: "2", medicationName: "Ibuprofeno 400mg", manufacturer: "Laboratório Y", uploadDate: "14/04/2026", status: "processing" },
  { id: "3", medicationName: "Amoxicilina 875mg", manufacturer: "Laboratório W", uploadDate: "13/04/2026", status: "error" },
  { id: "4", medicationName: "Losartana Potássica 50mg", manufacturer: "Laboratório K", uploadDate: "12/04/2026", status: "processed", chatRoute: "chat-losartana" },
]

const statusConfig = {
  processed: { 
    label: "Processado", 
    variant: "default" as const, 
    className: "bg-emerald-100 text-emerald-700 border-emerald-200",
    canChat: true
  },
  processing: { 
    label: "Processando", 
    variant: "secondary" as const, 
    className: "bg-amber-100 text-amber-700 border-amber-200",
    canChat: false
  },
  error: { 
    label: "Falha no Upload", 
    variant: "destructive" as const, 
    className: "bg-red-100 text-red-700 border-red-200",
    canChat: false
  },
}

export function DashboardView({ onLogout }: DashboardViewProps) {
  const [activeNav, setActiveNav] = useState<NavItem>("bulas")
  const [bulas, setBulas] = useState<Bula[]>(mockBulas)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [medicationName, setMedicationName] = useState("")
  const [manufacturer, setManufacturer] = useState("")
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  const handleDelete = (id: string) => {
    setBulas(bulas.filter(b => b.id !== id))
  }

  const handleRetry = (id: string) => {
    setBulas(bulas.map(b => b.id === id ? { ...b, status: "processing" as const } : b))
  }

  const handleFileSelect = () => {
    setSelectedFile("documento_selecionado.pdf")
  }

  const handleConfirmUpload = () => {
    if (!medicationName.trim()) {
      return
    }

    const newBula: Bula = {
      id: String(Date.now()),
      medicationName: medicationName.trim(),
      manufacturer: manufacturer.trim() || "Não especificado",
      uploadDate: new Date().toLocaleDateString("pt-BR"),
      status: "processing"
    }
    setBulas([newBula, ...bulas])
    setShowUploadModal(false)
    setMedicationName("")
    setManufacturer("")
    setSelectedFile(null)
  }

  const handleChatWithBula = (bula: Bula) => {
    if (bula.chatRoute) {
      setActiveNav(bula.chatRoute)
    } else {
      setActiveNav("chat-general")
    }
  }

  const handleNavClick = (nav: NavItem) => {
    setActiveNav(nav)
    setMobileMenuOpen(false)
  }

  const isChat = activeNav === "chat-general" || activeNav === "chat-losartana"

  const SidebarContent = () => (
    <>
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sidebar-primary/20 flex items-center justify-center">
            <Pill className="w-5 h-5 text-sidebar-primary" />
          </div>
          <div>
            <h1 className="font-bold text-lg">Bula AI</h1>
            <p className="text-xs text-sidebar-foreground/60">Healthcare Intelligence</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          <li>
            <button
              onClick={() => handleNavClick("bulas")}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all",
                activeNav === "bulas"
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <FileText className="w-5 h-5" />
              Minhas Bulas
            </button>
          </li>

          <li className="pt-4">
            <div className="px-4 py-2 text-xs font-semibold text-sidebar-foreground/50 uppercase tracking-wide">
              Chats
            </div>
            <button
              onClick={() => handleNavClick("chat-general")}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium transition-all mt-2",
                activeNav === "chat-general"
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <MessageCircle className="w-5 h-5" />
              Chat AI (Geral)
            </button>
            <button
              onClick={() => handleNavClick("chat-losartana")}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium transition-all mt-1",
                activeNav === "chat-losartana"
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <MessageCircle className="w-5 h-5" />
              Losartana Potássica
            </button>
          </li>
        </ul>
      </nav>

      <div className="p-4 border-t border-sidebar-border">
        <div className="flex items-center gap-3 px-2 py-2 rounded-lg bg-sidebar-accent/30">
          <div className="w-8 h-8 rounded-full bg-sidebar-primary/20 flex items-center justify-center text-xs font-medium text-sidebar-primary">
            JS
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">João Silva</p>
            <p className="text-xs text-sidebar-foreground/60 truncate">joao@email.com</p>
          </div>
        </div>
      </div>
    </>
  )

  return (
    <div className="min-h-screen flex bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-64 bg-sidebar text-sidebar-foreground flex-col border-r border-sidebar-border">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar (Sheet) */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-72 p-0 bg-sidebar text-sidebar-foreground">
          <SheetHeader className="sr-only">
            <SheetTitle>Menu de navegação</SheetTitle>
          </SheetHeader>
          <div className="flex flex-col h-full">
            <SidebarContent />
          </div>
        </SheetContent>
      </Sheet>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 sm:h-16 border-b border-border bg-card flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon-sm"
              className="md:hidden"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="w-5 h-5" />
              <span className="sr-only">Abrir menu</span>
            </Button>
            <div className="min-w-0">
              <h2 className="text-base sm:text-lg font-semibold text-foreground truncate">
                {activeNav === "bulas" 
                  ? "Minhas Bulas" 
                  : activeNav === "chat-general"
                  ? "Chat AI - Geral"
                  : "Chat AI - Losartana Potássica"}
              </h2>
              <p className="text-xs sm:text-sm text-muted-foreground hidden sm:block">
                {activeNav === "bulas"
                  ? "Gerencie suas bulas de medicamentos"
                  : "Converse com a IA sobre seus medicamentos"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <Avatar className="h-8 w-8 sm:h-9 sm:w-9">
              <AvatarImage src="" alt="User" />
              <AvatarFallback className="bg-primary/10 text-primary text-xs sm:text-sm font-medium">JS</AvatarFallback>
            </Avatar>
            <Button variant="outline" size="sm" onClick={onLogout} className="hidden sm:flex">
              <LogOut className="w-4 h-4 mr-2" />
              Sair
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={onLogout} className="sm:hidden">
              <LogOut className="w-4 h-4" />
              <span className="sr-only">Sair</span>
            </Button>
          </div>
        </header>

        {/* Global Medical Warning for Chat Views */}
        {isChat && <MedicalWarning />}

        {/* Content Area */}
        <main className="flex-1 overflow-auto">
          {activeNav === "bulas" ? (
            <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
                <div>
                  <h3 className="text-xl sm:text-2xl font-bold text-foreground">Minhas Bulas</h3>
                  <p className="text-sm text-muted-foreground mt-1">{bulas.length} bulas carregadas</p>
                </div>
                <Button onClick={() => setShowUploadModal(true)} size="default" className="gap-2 w-full sm:w-auto">
                  <Upload className="w-4 h-4" />
                  Adicionar nova bula
                </Button>
              </div>

              {/* Grid of Bula Cards OR Empty State */}
              {bulas.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                  {bulas.map((bula) => {
                    const config = statusConfig[bula.status]
                    const isError = bula.status === "error"
                    
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
                          <CardTitle className="text-base sm:text-lg line-clamp-2">{bula.medicationName}</CardTitle>
                          <CardDescription className="text-xs">{bula.manufacturer}</CardDescription>
                        </CardHeader>
                        <CardContent className="flex-1 pb-3 space-y-3">
                          <div className="text-sm text-muted-foreground">
                            <p className="text-xs text-muted-foreground/60">Data de upload</p>
                            <p className="font-medium">{bula.uploadDate}</p>
                          </div>
                          <div>
                            <Badge 
                              variant={config.variant}
                              className={cn("gap-1.5 text-xs", config.className)}
                            >
                              {bula.status === "processing" && <Loader2 className="w-3 h-3 animate-spin" />}
                              {bula.status === "processed" && <Check className="w-3 h-3" />}
                              {config.label}
                            </Badge>
                          </div>
                        </CardContent>
                        <div className="border-t border-border px-4 sm:px-6 py-3 flex gap-2">
                          {isError ? (
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="flex-1 gap-2 text-xs h-9"
                              onClick={() => handleRetry(bula.id)}
                            >
                              <RefreshCw className="w-3.5 h-3.5" />
                              Tentar Novamente
                            </Button>
                          ) : (
                            <Button 
                              variant="default" 
                              size="sm" 
                              className={cn(
                                "flex-1 gap-2 text-xs h-9",
                                !config.canChat && "opacity-50 cursor-not-allowed"
                              )}
                              disabled={!config.canChat}
                              onClick={() => handleChatWithBula(bula)}
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                              Conversar
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="icon-sm"
                            onClick={() => handleDelete(bula.id)}
                            className="text-muted-foreground hover:text-destructive h-9 w-9"
                          >
                            <Trash2 className="w-4 h-4" />
                            <span className="sr-only">Excluir {bula.medicationName}</span>
                          </Button>
                        </div>
                      </Card>
                    )
                  })}
                </div>
              ) : (
                /* Empty State */
                <Card className="border-dashed border-2">
                  <CardContent className="flex flex-col items-center justify-center py-16 sm:py-24">
                    <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-muted/50 flex items-center justify-center mb-6">
                      <FileSearch className="w-10 h-10 sm:w-12 sm:h-12 text-muted-foreground/50" />
                    </div>
                    <h3 className="text-lg sm:text-xl font-semibold text-foreground mb-2 text-center">
                      Nenhuma bula cadastrada ainda
                    </h3>
                    <p className="text-sm text-muted-foreground mb-6 text-center max-w-sm">
                      Comece enviando sua primeira bula de medicamento para conversar com a IA sobre dosagens, efeitos e mais.
                    </p>
                    <Button 
                      variant="secondary" 
                      size="lg" 
                      onClick={() => setShowUploadModal(true)}
                      className="gap-2"
                    >
                      <Upload className="w-4 h-4" />
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
          <div 
            className="absolute inset-0 bg-foreground/50 backdrop-blur-sm"
            onClick={() => {
              setShowUploadModal(false)
              setMedicationName("")
              setManufacturer("")
              setSelectedFile(null)
            }}
          />
          <Card className="relative z-10 w-full max-w-lg shadow-2xl">
            {/* Close button - absolute top-right */}
            <Button 
              variant="ghost" 
              size="icon-sm" 
              className="absolute top-3 right-3 z-10"
              onClick={() => {
                setShowUploadModal(false)
                setMedicationName("")
                setManufacturer("")
                setSelectedFile(null)
              }}
            >
              <X className="w-4 h-4" />
              <span className="sr-only">Fechar</span>
            </Button>
            <CardHeader className="pr-12">
              <CardTitle className="text-lg">Adicionar nova bula</CardTitle>
              <CardDescription>Preencha as informações e envie o PDF</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground block mb-2">
                  Nome do medicamento <span className="text-destructive">*</span>
                </label>
                <Input
                  type="text"
                  placeholder="Ex: Losartana Potássica 50mg"
                  value={medicationName}
                  onChange={(e) => setMedicationName(e.target.value)}
                  className="text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground block mb-2">
                  Fabricante
                </label>
                <Input
                  type="text"
                  placeholder="Ex: Laboratório X"
                  value={manufacturer}
                  onChange={(e) => setManufacturer(e.target.value)}
                  className="text-sm"
                />
              </div>
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={(e) => { e.preventDefault(); setIsDragOver(false); handleFileSelect() }}
                onClick={handleFileSelect}
                className={cn(
                  "border-2 border-dashed rounded-xl p-6 sm:p-8 text-center transition-all cursor-pointer",
                  isDragOver 
                    ? "border-primary bg-primary/5" 
                    : selectedFile
                    ? "border-primary/50 bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-muted/50"
                )}
              >
                {selectedFile ? (
                  <>
                    <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-primary/20 flex items-center justify-center mx-auto mb-3">
                      <Check className="w-5 h-5 sm:w-6 sm:h-6 text-primary" />
                    </div>
                    <h3 className="text-sm font-medium text-foreground mb-1">
                      Arquivo selecionado
                    </h3>
                    <p className="text-xs text-primary font-medium">
                      {selectedFile}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Clique para trocar o arquivo
                    </p>
                  </>
                ) : (
                  <>
                    <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                      <CloudUpload className="w-5 h-5 sm:w-6 sm:h-6 text-primary" />
                    </div>
                    <h3 className="text-sm font-medium text-foreground mb-1">
                      Arraste e solte seu arquivo
                    </h3>
                    <p className="text-xs text-muted-foreground mb-2">
                      ou clique para selecionar
                    </p>
                    <p className="text-xs text-muted-foreground">
                      PDF até 10MB
                    </p>
                  </>
                )}
              </div>

              {/* Confirm Upload Button */}
              <Button
                onClick={handleConfirmUpload}
                className="w-full"
                size="lg"
                disabled={!medicationName.trim() || !selectedFile}
              >
                <Upload className="w-4 h-4 mr-2" />
                Confirmar Envio
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

// General Chat Component
function GeneralChat() {
  const [inputValue, setInputValue] = useState("")
  const [isTyping] = useState(true)

  const handleSpeak = (text: string) => {
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'pt-BR'
      speechSynthesis.speak(utterance)
    }
  }

  const welcomeMessage = "Olá! Sou o Bula AI, seu assistente de saúde. Como posso ajudá-lo hoje?"

  return (
    <div className="h-full flex flex-col">
      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-6">
        {/* AI Welcome Message */}
        <div className="flex gap-3 sm:gap-4">
          <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
            <span className="text-[10px] sm:text-xs font-semibold text-primary">AI</span>
          </div>
          <div className="flex-1 space-y-2 min-w-0 max-w-[85%] sm:max-w-none">
            <span className="text-sm font-medium text-foreground">Bula AI</span>
            <div className="bg-card border border-border rounded-lg p-3 sm:p-4 space-y-3">
              <p className="text-sm text-foreground leading-relaxed">{welcomeMessage}</p>
              <div className="flex justify-end pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSpeak(welcomeMessage)}
                  className="text-muted-foreground hover:text-primary h-7 px-2 gap-1"
                  title="Ouvir esta mensagem"
                >
                  <Volume2 className="w-3.5 h-3.5" />
                  <span className="text-[10px] hidden sm:inline">Ouvir</span>
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Typing Indicator (Demo) */}
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
            placeholder="Digite sua pergunta..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="h-10 sm:h-12 text-sm"
          />
          <Button
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
