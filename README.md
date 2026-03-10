# Laris - Artigos em Áudio

Converta artigos científicos em áudio narrado. Desenvolvido com foco em **acessibilidade** para pessoas com baixa visão.

## O que o Laris faz?

1. **Extrai texto** de PDFs, DOCX ou TXT
2. **Detecta o idioma** automaticamente
3. **Traduz para português** (se necessário) - usando Google Translate
4. **Gera narração em voz** natural (PT-BR, feminino ou masculino)
5. **Sempre entrega um único MP3** (mesmo para textos longos)

Tudo com poucos cliques, interface limpa, botões grandes, alto contraste.

---

## Requisitos

- **Python 3.10+** ([Download](https://python.org))
- **Node.js 18+** ([Download](https://nodejs.org))
- **FFmpeg** (obrigatório para textos longos)

### Instalando FFmpeg

**Windows:**
1. Baixe de https://github.com/BtbN/FFmpeg-Builds/releases (escolha `ffmpeg-master-latest-win64-gpl.zip`)
2. Extraia para `C:\ffmpeg`
3. Adicione `C:\ffmpeg\bin` ao PATH:
   - Pesquise "variáveis de ambiente" no Windows
   - Clique em "Editar variáveis de ambiente do sistema"
   - Clique em "Variáveis de Ambiente"
   - Na seção "Variáveis do sistema", selecione "Path" e clique em "Editar"
   - Clique em "Novo" e adicione `C:\ffmpeg\bin`
   - Clique OK em todas as janelas
4. Reinicie o terminal e teste: `ffmpeg -version`

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install ffmpeg
```

---

## Instalação

### 1. Clone ou baixe o projeto

```bash
cd laris
```

### 2. Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate

# Ativar (macOS/Linux)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

Se quiser definir a API explicitamente no frontend, crie `frontend/.env.local` com:

```bash
VITE_API_URL=https://laris-api.vercel.app
```

---

## Como usar

### Iniciar o Laris

**Terminal 1 - Backend:**
```bash
cd backend
venv\Scripts\activate  # ou: source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

O navegador abrirá em `http://localhost:5173` (ou porta indicada pelo Vite)

### Verificar Instalação

Acesse http://localhost:8000/api/health e verifique:

```json
{
  "ok": true,
  "system": {
    "edge_tts_available": true,
    "ffmpeg_available": true,
    "google_translate_available": true
  }
}
```

## Deploy na Vercel

No projeto do frontend na Vercel, configure a variavel de ambiente abaixo:

```bash
VITE_API_URL=https://laris-api.vercel.app
```

Passos:

1. Abra o projeto do frontend na Vercel.
2. Entre em `Settings > Environment Variables`.
3. Adicione `VITE_API_URL`.
4. Use o valor `https://laris-api.vercel.app`.
5. Salve as alteracoes e faca um novo deploy.

## Deploy do Backend na Railway

O backend FastAPI pode ser publicado na Railway usando o arquivo `railway.json`.

Comando de start:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Passos:

1. Crie um novo projeto na Railway e importe este repositorio.
2. Mantenha o deploy com o `railway.json` da raiz do projeto.
3. Configure `CORS_ORIGINS` com a URL publica do frontend.
4. Se quiser forcar o diretorio de trabalho para arquivos gerados, defina `OUTPUTS_DIR=/tmp/laris-outputs`.
5. Depois do deploy, valide o endpoint `GET /health`.

Observacoes:

- A Railway injeta a variavel `PORT`, e o comando usa `8000` como fallback local.
- O backend ja expõe `GET /health` para uptime checks.
- Em ambiente de deploy, os arquivos temporarios usam `OUTPUTS_DIR`, `TMPDIR` ou `/tmp`.

### Passo a passo

1. **Envie seu arquivo** (PDF, DOCX ou TXT)
2. **Veja o idioma detectado** (ex: "Inglês")
3. **Clique em "Gerar Áudio"**
4. **Aguarde a tradução e geração** (progresso mostrado em tempo real)
5. **Baixe o MP3** ou ouça diretamente no navegador

---

## Atalhos de Teclado

| Atalho | Ação |
|--------|------|
| `Alt + U` | Abrir seleção de arquivo |
| `Alt + G` | Gerar áudio |
| `Alt + D` | Baixar áudio |
| `Tab` | Navegar entre elementos |
| `Enter` | Ativar botão focado |

---

## Recursos de Acessibilidade

- **Botões grandes** (mínimo 60px de altura)
- **Textos grandes** (mínimo 18px, ajustável)
- **Alto contraste** por padrão
- **Modo Super Contraste** (amarelo sobre preto)
- **Ajuste de fonte** (A+ / A-)
- **Navegação por teclado** completa
- **Compatível com leitores de tela** (ARIA labels)
- **Mensagens de status** anunciáveis (aria-live)

---

## Solução de Problemas

### "Não consegui ler esse PDF"

O PDF pode estar:
- Protegido por senha
- Escaneado (imagem, não texto)
- Corrompido

**Solução:** Copie o texto do PDF manualmente e salve como `.txt`

### "ffmpeg não está instalado"

Para textos longos, o Laris precisa do ffmpeg para concatenar as partes do áudio em um único MP3.

Siga as instruções de instalação do FFmpeg acima.

### "Serviço de tradução não disponível"

Instale o deep-translator:

```bash
pip install deep-translator
```

### Erro de conexão

Verifique se o backend está rodando:
- Deve haver uma janela de terminal mostrando `Uvicorn running on http://127.0.0.1:8001`

---

## Privacidade

- **Processamento local:** Extração de texto é feita localmente
- **Tradução:** Usa Google Translate (requer internet)
- **TTS:** Usa Microsoft Edge TTS (requer internet)

---

## Estrutura do Projeto

```
laris/
├── backend/           # API FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── extract.py    # Extração de texto
│   │   │   ├── tts.py        # Geração de áudio (com tradução)
│   │   │   └── translate.py  # Tradução standalone
│   │   ├── services/
│   │   │   ├── tts_service.py    # Lógica de TTS + ffmpeg
│   │   │   └── translation.py    # Google Translate
│   │   └── utils/
│   ├── tests/
│   └── requirements.txt
├── frontend/          # React + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   └── styles/
│   └── package.json
├── outputs/           # Arquivos gerados
└── README.md
```

---

## Tecnologias

**Backend:**
- Python 3.10+
- FastAPI
- pypdf / pdfplumber (extração de PDF)
- python-docx (extração de DOCX)
- langdetect (detecção de idioma)
- deep-translator (Google Translate)
- edge-tts (síntese de voz Microsoft)
- ffmpeg (concatenação de áudio)

**Frontend:**
- React 18
- TypeScript
- Vite

---

## Teste Rápido

1. Abra o app no navegador
2. Faça upload de um PDF em inglês
3. O sistema deve:
   - Mostrar "Idioma detectado: Inglês"
   - Mostrar "Traduzindo de Inglês para Português..."
   - Mostrar "Gerando parte 1/N..."
   - Mostrar "Juntando partes em 1 MP3..."
4. Baixe e ouça o MP3 final

---

## Créditos

- **Vozes:** Microsoft Edge Neural TTS
- **Tradução:** Google Translate (via deep-translator)

---

## Licença

MIT License - Use livremente, modifique, distribua.

---

*Laris - Feito com acessibilidade em mente.*
