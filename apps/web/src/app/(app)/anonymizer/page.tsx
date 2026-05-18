import { AnonymizerForm } from "./form";

export default function AnonymizerPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Preview de anonimização</h1>
        <p className="text-sm text-muted-foreground">
          Cole um trecho de texto pra ver como ele fica depois do pipeline
          regex + LLM. Útil pra calibrar antes de mandar peças reais ao
          analisador.
        </p>
      </header>
      <AnonymizerForm />
    </div>
  );
}
