# Laris - Artigos em Áudio

Converta artigos científicos em áudio narrado. Desenvolvido com foco em **acessibilidade** para pessoas com baixa visão.

## O que o Laris faz?

1. **Extrai texto** de PDFs, DOCX ou TXT
2. **Detecta o idioma** automaticamente
3. **Traduz para português** (se necessário) - funciona offline
4. **Gera narração em voz** natural (PT-BR, feminino ou masculino)
5. **Permite baixar** o áudio (MP3) e o texto traduzido (TXT)

Tudo com poucos cliques, interface limpa, botões grandes, alto contraste.

---

## Requisitos

- **Python 3.11+** ([Download](https://python.org))
- **Node.js 18+** ([Download](https://nodejs.org))
- **FFmpeg** (opcional, para textos muito longos)

### Instalando FFmpeg

**Windows:**
```bash
winget install FFmpeg
```

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

### 2. Instale as dependências

**Windows:**
```bash
setup.bat
```

**macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

---

## Como usar

### Iniciar o Laris

**Windows:**
```bash
run.bat
```

**macOS/Linux:**
```bash
chmod +x run.sh
./run.sh
```

O navegador abrirá automaticamente em `http://localhost:5173`

### Passo a passo

1. **Envie seu arquivo** (PDF, DOCX ou TXT)
2. **Confirme a tradução** (se o texto não estiver em português)
3. **Escolha a voz** (feminina ou masculina) e ajuste a velocidade
4. **Clique em "Gerar Áudio"**
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

### "Pacote de tradução não instalado"

Na primeira vez que você traduzir, o Laris precisa baixar o modelo de tradução (~100 MB).

Clique em **"Instalar pacote de tradução"** e aguarde.

### Áudio em partes (ZIP)

Para textos muito longos, o Laris precisa dividir o áudio em partes.

- **Com FFmpeg/pydub instalados:** O Laris concatena automaticamente em um único MP3
- **Sem FFmpeg/pydub:** O Laris gera um ZIP com as partes separadas (parte_01.mp3, parte_02.mp3, etc.)

Para ter áudio único, instale FFmpeg seguindo as instruções acima e também:

```bash
pip install pydub
```

**Nota:** O ZIP funciona perfeitamente. Basta extrair e tocar os arquivos em ordem.

### Erro de conexão

Verifique se o backend está rodando:
- Deve haver uma janela de terminal mostrando o servidor Uvicorn

---

## Privacidade

- **Processamento local:** Seus arquivos não são enviados para servidores externos
- **Tradução offline:** Usa Argos Translate, que funciona sem internet
- **TTS:** Usa Microsoft Edge TTS, que **requer conexão com a internet** para gerar a voz

---

## Estrutura do Projeto

```
laris/
├── backend/           # API FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
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
├── run.bat            # Iniciar (Windows)
├── run.sh             # Iniciar (macOS/Linux)
├── setup.bat          # Instalar (Windows)
├── setup.sh           # Instalar (macOS/Linux)
└── README.md
```

---

## Tecnologias

**Backend:**
- Python 3.11+
- FastAPI
- pypdf / pdfplumber (extração de PDF)
- python-docx (extração de DOCX)
- langdetect (detecção de idioma)
- argostranslate (tradução offline)
- edge-tts (síntese de voz)
- pydub (processamento de áudio)

**Frontend:**
- React 18
- TypeScript
- Vite

---

## Executando os Testes

```bash
cd backend
source venv/bin/activate  # ou: venv\Scripts\activate (Windows)
pytest tests/ -v
```

---

## Créditos

- **Vozes:** Microsoft Edge Neural TTS
- **Tradução:** Argos Translate (MIT License)
- **Ícones:** Unicode Emoji

---

## Licença

MIT License - Use livremente, modifique, distribua.

---

## Suporte

Se encontrar problemas, verifique:
1. Os logs no terminal do backend
2. O console do navegador (F12)
3. Se todas as dependências estão instaladas

---

*Laris - Feito com acessibilidade em mente.*
