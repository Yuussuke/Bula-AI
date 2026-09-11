import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthView } from "@/components/auth-view";

function renderAuthView(): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthView />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AuthView password requirements", () => {
  it("shows and applies the registration password length limits", async () => {
    const user = userEvent.setup();
    renderAuthView();

    await user.click(screen.getByRole("tab", { name: "Cadastrar" }));

    const passwordInput = screen.getByLabelText("Senha");
    expect(passwordInput).toHaveAttribute("minlength", "8");
    expect(passwordInput).toHaveAttribute("maxlength", "64");
    expect(passwordInput).toHaveAccessibleDescription(
      "Use de 8 a 64 caracteres. Letras, números, espaços e símbolos são aceitos. " +
        "Senhas encontradas em vazamentos conhecidos serão recusadas."
    );
  });
});
