# medscribe

MVP open source para transformar gravações de consultas médicas em **rascunhos editáveis** de prontuário (SOAP), receita e pedidos de exame. A interface é em português do Brasil.

O fluxo é: **áudio → transcrição diarizada (pyannote.ai) → extração estruturada (Claude) → revisão humana no navegador**.

> **Aviso:** este software gera rascunhos para revisão — não substitui julgamento clínico. Não use com dados reais de pacientes sem avaliar LGPD, consentimento e contratos com os provedores externos.

## Pré-requisitos

| Ferramenta | Versão mínima | Uso |
|------------|---------------|-----|
| [Python](https://www.python.org/) | 3.12+ | API (FastAPI) |
| [uv](https://docs.astral.sh/uv/) | recente | dependências Python |
| [Node.js](https://nodejs.org/) | 20+ | frontend Next.js |
| npm | (vem com Node) | frontend |

## Chaves de API (obrigatórias)

O backend **não inicia** sem as duas chaves abaixo. Crie contas nos provedores e gere tokens de API.

### 1. pyannote.ai — transcrição e diarização

- **Site:** [https://pyannote.ai](https://pyannote.ai)
- **Variável:** `MEDSCRIBE_PYANNOTE_API_KEY`
- **Função:** envia o áudio da consulta, separa falantes (`SPEAKER_00`, `SPEAKER_01`, …) e devolve a transcrição turno a turno.
- **Documentação:** [https://docs.pyannote.ai](https://docs.pyannote.ai)

### 2. Anthropic — extração de documentos clínicos

- **Site:** [https://console.anthropic.com](https://console.anthropic.com)
- **Variável:** `MEDSCRIBE_ANTHROPIC_API_KEY`
- **Função:** lê a transcrição e gera JSON estruturado (SOAP, receita, exames) via Claude com saída tipada.
- **Modelo padrão:** `claude-sonnet-4-5` (`MEDSCRIBE_ANTHROPIC_MODEL`)
- **Documentação:** [https://docs.anthropic.com](https://docs.anthropic.com)

**Custo:** ambos os serviços são pagos por uso. Consulte a precificação de cada um antes de rodar consultas longas ou em volume.

## Configuração

Na raiz do repositório:

```bash
cp .env.example .env
```

Edite `.env` e preencha as chaves:

```env
MEDSCRIBE_PYANNOTE_API_KEY=sua-chave-pyannote
MEDSCRIBE_ANTHROPIC_API_KEY=sua-chave-anthropic
MEDSCRIBE_ANTHROPIC_MODEL=claude-sonnet-4-5
MEDSCRIBE_CORS_ORIGINS=["http://localhost:3000"]
```

Instale as dependências Python:

```bash
uv sync
```

Instale as dependências do frontend:

```bash
cd frontend
npm install
cd ..
```

### Variáveis de ambiente (referência)

| Variável | Obrigatória | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `MEDSCRIBE_PYANNOTE_API_KEY` | sim | — | Bearer token da pyannote.ai |
| `MEDSCRIBE_ANTHROPIC_API_KEY` | sim | — | API key da Anthropic |
| `MEDSCRIBE_ANTHROPIC_MODEL` | não | `claude-sonnet-4-5` | Modelo Claude para extração |
| `MEDSCRIBE_ANTHROPIC_MAX_TOKENS` | não | `8192` | Limite de tokens na resposta |
| `MEDSCRIBE_ANTHROPIC_BASE_URL` | não | `https://api.anthropic.com` | Base URL da API Anthropic |
| `MEDSCRIBE_PYANNOTE_BASE_URL` | não | `https://api.pyannote.ai` | Base URL da pyannote.ai |
| `MEDSCRIBE_PYANNOTE_POLL_INTERVAL_SECONDS` | não | `10` | Intervalo de polling do job pyannote |
| `MEDSCRIBE_PYANNOTE_POLL_TIMEOUT_SECONDS` | não | `600` | Timeout total do job pyannote |
| `MEDSCRIBE_CONSULTATION_OUTPUT_DIR` | não | `data/consultations` | Pasta onde consultas são persistidas |
| `MEDSCRIBE_CORS_ORIGINS` | não | `["http://localhost:3000"]` | Origens permitidas no CORS (JSON array) |

No frontend, opcionalmente:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `MEDSCRIBE_API_URL` | `http://localhost:8000` | URL da API para o proxy do Next.js |

## Executar

Abra **dois terminais**.

**Terminal 1 — API:**

```bash
uv run uvicorn app.main:app --reload
```

A API fica em `http://localhost:8000`. Documentação interativa: `http://localhost:8000/docs`.

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Abra `http://localhost:3000`.

## Como usar (interface)

1. Clique em **Gravar consulta** e autorize o microfone.
2. Encerre a gravação quando terminar a consulta (ou envie um arquivo de áudio, se habilitado).
3. Aguarde o processamento: transcrição → extração de documentos.
4. Revise e edite os rascunhos de **Prontuário (SOAP)**, **Receita** e **Requisição de exames**.
5. Preencha cabeçalho (paciente, médico, etc.) e use **Imprimir** quando estiver satisfeito.

Em modo desenvolvimento (`npm run dev`), uma cópia do áudio pode ser salva em `frontend/recordings/` para revisão de qualidade — essa pasta está no `.gitignore`.

## Como funciona

### Pipeline

```
Navegador          medscribe (API)              Serviços externos
    |                    |                              |
    | POST /consultations|                              |
    | (upload áudio)     | upload + job diarize         |
    | -----------------> | ---------------------------> | pyannote.ai
    | 202 { id }         |                              |
    |                    | [background] poll + format   |
    |                    | ---------------------------> | pyannote.ai
    |                    | grava transcript.txt         |
    |                    | messages.parse (Claude)      |
    |                    | ---------------------------> | Anthropic
    |                    | grava documents.json         |
    | GET /consultations/{id} (poll)                    |
    | -----------------> |                              |
    | status + rascunhos |                              |
    | <----------------- |                              |
```

Estados da consulta: `transcribing` → `extracting` → `succeeded` | `failed`.

A **transcrição diarizada não é exposta** na API pública — fica apenas em disco no servidor. O cliente recebe status e, quando pronto, os documentos estruturados.

### Armazenamento local

Cada consulta gera uma pasta:

```
data/consultations/{consultation_id}/
  meta.json         # id, status, timestamps, erro (se houver)
  transcript.txt    # transcrição para o LLM (não servida pela API)
  documents.json    # SOAP, receita e exames validados
```

A pasta `data/` está no `.gitignore` — nada de consulta real deve ir para o Git.

### Documentos gerados

| Documento | Conteúdo |
|-----------|----------|
| Prontuário | SOAP (subjetivo, objetivo, avaliação, plano) |
| Receita | lista de medicamentos (nome, dose, via, frequência, duração, instruções) |
| Exames | lista de pedidos (nome, indicação, instruções) |

O prompt instrui o modelo a **não inventar** dados clínicos ausentes na transcrição e a tratar falantes apenas como `SPEAKER_XX` (sem assumir quem é médico ou paciente).

### API HTTP

| Método | Caminho | Sucesso | Descrição |
|--------|---------|---------|-----------|
| `GET` | `/health` | 200 | Health check (`{"status": "ok"}`) |
| `POST` | `/consultations` | 202 | Envia áudio (`multipart/form-data`, campo `file`) |
| `GET` | `/consultations/{id}` | 200 | Consulta status e documentos |
| `POST` | `/consultations/{id}/extract` | 202 | Reprocessa só a extração (sem re-transcrever) |

Detalhes do contrato: [docs/adr/0002-consultation-pipeline.md](docs/adr/0002-consultation-pipeline.md).

Exemplo com `curl`:

```bash
curl -X POST http://localhost:8000/consultations \
  -F "file=@consulta.wav"

curl http://localhost:8000/consultations/{id}
```

## Bibliotecas e serviços de terceiros

### Serviços externos (APIs)

| Serviço | Uso no medscribe |
|---------|------------------|
| **[pyannote.ai](https://pyannote.ai)** | Upload de áudio, diarização e transcrição |
| **[Anthropic Claude](https://www.anthropic.com)** | Extração estruturada dos rascunhos clínicos |

Ao usar o software, áudio e transcrição são enviados a esses provedores conforme suas políticas de privacidade e termos de uso.

### Backend (Python)

| Biblioteca | Papel |
|------------|-------|
| [FastAPI](https://fastapi.tiangolo.com/) | API HTTP, upload, background tasks |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | SDK oficial — `messages.parse` com saída Pydantic |
| [httpx2](https://pypi.org/project/httpx2/) | Cliente HTTP para a API pyannote.ai |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Configuração via `.env` |

Gerenciamento de dependências: [uv](https://docs.astral.sh/uv/).

### Frontend (TypeScript)

| Biblioteca | Papel |
|------------|-------|
| [Next.js](https://nextjs.org/) | App Router, proxy `/consultations` → API |
| [React](https://react.dev/) | Interface de gravação e revisão de rascunhos |

APIs do navegador: `MediaRecorder` e `getUserMedia` para captura de áudio.

## Desenvolvimento

Testes e qualidade (Python):

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pylint app tests
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Limitações do MVP

- **Sem autenticação** — qualquer cliente que alcance a API pode criar consultas.
- **Background tasks** — se o processo da API encerrar no meio do pipeline, o status pode ficar preso em `transcribing` ou `extracting`.
- **Disco local** — não há fila durável nem storage compartilhado entre instâncias.
- **Rascunhos, não prontuário final** — sempre exija revisão humana antes de qualquer uso clínico.

## Estrutura do projeto

```
app/
  consultation/     # rotas e orquestração da consulta
  transcription/      # integração pyannote (interno, sem rota pública)
  extraction/         # prompt e schemas dos documentos
  clients/            # wrappers pyannote e Anthropic
frontend/             # UI Next.js (pt-BR)
docs/adr/             # decisões de arquitetura
tests/                # pytest (dados fake, sem rede)
```

## Licença

Ver [LICENSE](LICENSE).
