import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactElement, useState } from "react";

import { assignCurationRole, getCurationRoleHistory, listCurationUsers } from "@/api/curation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useIdempotencyKey } from "@/hooks/use-idempotency-key";
import { type AuthUser, useAuthStore } from "@/store/auth";

const labels: Record<AuthUser["role"], string> = {
  user: "Usuário",
  contributor: "Contribuidor",
  reviewer: "Curador",
  admin: "Administrador",
};

function Designation({ user }: { user: AuthUser }): ReactElement {
  const cache = useQueryClient();
  const operation = useIdempotencyKey();
  const [showHistory, setShowHistory] = useState(false);
  const [role, setRole] = useState<Exclude<AuthUser["role"], "admin">>(
    user.role === "admin" ? "user" : user.role
  );
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const change = useMutation({
    mutationFn: () =>
      assignCurationRole(
        user,
        role,
        reason,
        operation.keyFor(JSON.stringify({ id: user.id, expected_role: user.role, role, reason }))
      ),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["curation-users"] });
      void cache.invalidateQueries({ queryKey: ["curation-role-history", user.id] });
      operation.reset();
    },
    onError: (failure: Error) => {
      setError(failure.message);
      void cache.invalidateQueries({ queryKey: ["curation-users"] });
    },
  });
  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    setError("");
    change.mutate();
  };
  return (
    <article className="bg-card space-y-3 rounded-xl border p-4">
      <div>
        <h2 className="font-semibold">{user.name}</h2>
        <p className="text-muted-foreground text-sm">
          {user.email} · {labels[user.role]}
        </p>
      </div>
      {user.role !== "admin" && (
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[180px_1fr_auto]">
          <div>
            <Label htmlFor={`role-${user.id}`}>Perfil</Label>
            <select
              id={`role-${user.id}`}
              className="border-input bg-background h-10 w-full rounded-md border px-2 text-sm"
              disabled={change.isPending}
              value={role}
              onChange={(event) =>
                setRole(event.target.value as Exclude<AuthUser["role"], "admin">)
              }
            >
              <option value="user">Usuário</option>
              <option value="contributor">Contribuidor</option>
              <option value="reviewer">Curador</option>
            </select>
          </div>
          <div>
            <Label htmlFor={`assignment-${user.id}`}>Justificativa da designação</Label>
            <Input
              id={`assignment-${user.id}`}
              value={reason}
              minLength={3}
              maxLength={1000}
              required
              disabled={change.isPending}
              onChange={(event) => setReason(event.target.value)}
            />
          </div>
          <Button
            type="submit"
            className="self-end"
            disabled={change.isPending || reason.trim().length < 3 || role === user.role}
          >
            Salvar perfil
          </Button>
        </form>
      )}
      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}
      <Button
        variant="ghost"
        size="sm"
        aria-expanded={showHistory}
        onClick={() => setShowHistory((value) => !value)}
      >
        Histórico de designações
      </Button>
      {showHistory && <RoleHistory userId={user.id} />}
    </article>
  );
}

function RoleHistory({ userId }: { userId: number }): ReactElement {
  const [page, setPage] = useState(1);
  const history = useQuery({
    queryKey: ["curation-role-history", userId, page],
    queryFn: () => getCurationRoleHistory(userId, page),
  });
  if (history.isPending) return <p role="status">Carregando histórico…</p>;
  if (history.isError)
    return (
      <p role="alert">
        Não foi possível carregar o histórico.{" "}
        <Button variant="link" onClick={() => void history.refetch()}>
          Tentar novamente
        </Button>
      </p>
    );
  return (
    <div className="space-y-3 text-sm">
      {history.data.length === 0 && <p>Nenhuma designação nesta página.</p>}
      <ol className="space-y-3">
        {history.data.map((event) => (
          <li key={event.id} className="rounded border p-3">
            <p>
              {labels[event.previous_role]} → {labels[event.assigned_role]}
            </p>
            <p>{event.reason}</p>
            <p className="text-muted-foreground text-xs">
              {event.actor_name ??
                (event.actor_id === null
                  ? "Autor não registrado na versão anterior"
                  : `Responsável ID ${event.actor_id} (nome não registrado)`)}{" "}
              · {new Date(event.created_at).toLocaleString("pt-BR")}
            </p>
            <details className="mt-1 text-xs">
              <summary className="cursor-pointer">Dados de auditoria</summary>
              <p className="break-all">Registro: {event.id}</p>
              <p>Perfil do responsável: {event.actor_role ?? "Não registrado"}</p>
              <p className="break-all">Operação: {event.operation_id ?? "Registro anterior"}</p>
              {event.request_fingerprint && (
                <p className="break-all">Hash da solicitação: {event.request_fingerprint}</p>
              )}
            </details>
          </li>
        ))}
      </ol>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page === 1}
          onClick={() => setPage((value) => value - 1)}
        >
          Designações anteriores
        </Button>
        <span>Página {page}</span>
        <Button
          variant="outline"
          size="sm"
          disabled={history.data.length < 20}
          onClick={() => setPage((value) => value + 1)}
        >
          Mais designações
        </Button>
      </div>
    </div>
  );
}

export function CurationUsersPage(): ReactElement {
  const isAdmin = useAuthStore((state) => state.user?.role === "admin");
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const users = useQuery({
    queryKey: ["curation-users", query, page],
    queryFn: () => listCurationUsers(query, page),
    enabled: isAdmin,
  });
  if (!isAdmin) return <p role="alert">Esta área é restrita ao administrador.</p>;
  return (
    <section className="space-y-5">
      <h1 className="text-2xl font-semibold">Designação de Contribuidores e Curadores</h1>
      <p className="text-muted-foreground text-sm">
        Atribua Curador a especialistas da saúde designados para a conferência documental. O sistema
        registra sua justificativa; não verifica automaticamente a formação profissional. O usuário
        deve atualizar a página para ver o novo perfil.
      </p>
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          setQuery(input.trim());
          setPage(1);
        }}
      >
        <Input
          aria-label="Buscar usuário por e-mail"
          placeholder="Buscar por e-mail"
          value={input}
          onChange={(event) => setInput(event.target.value)}
        />
        <Button type="submit" variant="outline">
          Buscar
        </Button>
      </form>
      {users.isPending ? (
        <p role="status">Carregando usuários…</p>
      ) : users.isError ? (
        <p role="alert">
          Falha ao carregar usuários.{" "}
          <Button variant="link" onClick={() => void users.refetch()}>
            Tentar novamente
          </Button>
        </p>
      ) : (
        <>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              disabled={page === 1}
              onClick={() => setPage((value) => value - 1)}
            >
              Anterior
            </Button>
            <span className="self-center text-sm">Página {page}</span>
            <Button
              variant="outline"
              disabled={users.data.length < 20}
              onClick={() => setPage((value) => value + 1)}
            >
              Próxima
            </Button>
          </div>
          {users.data.length === 0 && <p>Nenhum usuário encontrado.</p>}
          {users.data.map((user) => (
            <Designation key={`${user.id}-${user.role}`} user={user} />
          ))}
        </>
      )}
    </section>
  );
}
