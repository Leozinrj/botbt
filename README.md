# 🤖 Bot BT - Sistema Automatizado para Tibia

Bot automatizado com Arduino Leonardo HID para controle de mouse e teclado no Tibia.

## 📋 Estrutura do Projeto

```
botbt/
├── arduino_leonardo/          # Código do Arduino Leonardo
│   ├── platformio.ini        # Configuração do PlatformIO
│   └── src/
│       └── main.cpp          # Firmware HID (Mouse + Keyboard)
│
├── scripts/                   # Bots Python
│   ├── amazon_cave.py        # Bot Amazon Cave (PRINCIPAL)
│   ├── mummy.py              # Bot Mummy Hunt (18 flags)
│   ├── amazom.ino            # Código Arduino (backup)
│   ├── requirements.txt      # Dependências Python
│   └── README.md             # Documentação detalhada
│
├── enemy/                     # Imagens dos inimigos
│   ├── amazon.png
│   ├── witch.png
│   ├── valkyrie.png
│   ├── bonebeast.png
│   ├── mummy.png
│   └── scarab.png
│
├── flags/                     # Imagens das flags de navegação
│   ├── amazon_camp/          # 22 flags Amazon Camp
│   │   ├── am_a1.png - am_a7.png   (parte superior)
│   │   ├── am_s1.png - am_s14.png  (subterrâneo)
│   │   └── subida1.png
│   └── flag1.png - flag18.png     (flags mummy)
│
├── loot/                      # Imagens de loot
│   ├── am_loot1.png
│   ├── am_loot2.png
│   └── am_loot3.png
│
└── healings/                  # Sistema de detecção de HP
    ├── hpcheio.png
    ├── hp80p.png
    ├── hpmedio.png
    └── hpbaixo.png
```

## 🔧 Hardware Necessário

- **Arduino Leonardo** ou **Pro Micro** (ATmega32u4)
- Cabo USB para conexão
- PC com Windows

## 📦 Instalação

### 1. Instalar Python e Dependências

```bash
cd scripts
pip install -r requirements.txt
```

**Dependências:**
- `pyautogui` - Controle de mouse e detecção de imagens
- `pyserial` - Comunicação serial com Arduino
- `opencv-python` - Processamento de imagens
- `numpy` - Cálculos numéricos
- `pillow` - Manipulação de imagens

### 2. Programar o Arduino Leonardo

#### Opção A: Usando PlatformIO (Recomendado)

```bash
cd arduino_leonardo
pio run --target upload
```

#### Opção B: Usando Arduino IDE

1. Abra `scripts/amazom.ino` no Arduino IDE
2. Selecione **Tools → Board → Arduino Leonardo**
3. Selecione a porta COM correta
4. Clique em **Upload** (Ctrl+U)

### 3. Configurar a Porta Serial

Verifique qual porta COM o Arduino está usando:

**Windows PowerShell:**
```powershell
[System.IO.Ports.SerialPort]::getportnames()
```

Edite o arquivo do bot e ajuste a porta:
```python
COM_PORT = "COM13"  # Ajuste conforme sua porta
BAUD_RATE = 115200
```

## 🎮 Como Usar

### Bot Amazon Cave (Principal)

Sistema completo com 25 flags, prioridades de inimigos e coleta de loot.

```bash
cd scripts
python amazon_cave.py
```

**Características:**
- ✅ 7 flags superiores (am_a1 → am_a7)
- ✅ 18 flags subterrâneas (rota completa)
- ✅ Sistema de prioridades: witch > valkyrie > amazon
- ✅ Clique ESQUERDO para inimigos e flags
- ✅ Clique DIREITO para loot
- ✅ Tecla 9 (2x) após cada combate
- ✅ Delays otimizados (-30%)
- ✅ Mouse move para centro após clicar em flag
- ✅ Sistema de interrupção/retomada

### Bot Mummy Hunt

Bot para caçar múmias em 18 flags.

```bash
cd scripts
python mummy.py
```

**Características:**
- ✅ 18 flags de navegação
- ✅ Healing automático
- ✅ Detecção de mummy, scarab, bonebeast
- ✅ Sistema de backslash após combate
- ✅ Interrupt/resume system

## 🎯 Sistema de Prioridades (Amazon Cave)

O bot detecta e prioriza inimigos automaticamente:

1. **Witch** (prioridade 3) - Ataca primeiro
2. **Valkyrie** (prioridade 2) - Média prioridade
3. **Amazon** (prioridade 1) - Prioridade comum

Quando detecta um inimigo durante navegação, o bot:
1. Pausa a navegação
2. Ataca o inimigo de maior prioridade
3. Aguarda 8 segundos de combate
4. Pressiona tecla 9 duas vezes
5. Coleta loot (se houver)
6. Retoma a navegação de onde parou

## 🖱️ Protocolo Arduino HID

O Arduino Leonardo responde aos seguintes comandos via Serial (115200 baud):

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `MA x y` | Move mouse absoluto | `MA 1024 768` |
| `M dx dy` | Move mouse relativo | `M 10 -5` |
| `CL` | Clique esquerdo | `CL` |
| `CR` | Clique direito | `CR` |
| `CM` | Clique do meio | `CM` |
| `CD` | Duplo clique | `CD` |
| `KT key` | Pressiona tecla ASCII | `KT 9` |
| `K KEY` | Tecla especial | `K ENTER` |
| `T texto` | Digita texto | `T hello` |
| `S ms` | Delay | `S 1000` |

## ⚙️ Configurações

### Ajustar Velocidade

No arquivo `amazon_cave.py`:

```python
COMBAT_DELAY = 8.0          # Tempo de combate (segundos)
LOOT_CHECK_TIME = 1.5       # Tempo para verificar loot
```

### Ajustar Confidence de Detecção

```python
CONFIDENCE = 0.8            # 0.7 = mais sensível, 0.9 = mais preciso
```

### Delays Entre Flags

Os delays já estão otimizados (-30%). Para ajustar manualmente:

```python
# Em UPPER_ROUTE e UNDERGROUND_ROUTE
("am_a2", 8),  # 8 segundos * 0.7 = 5.6s efetivo
```

## 🐛 Troubleshooting

### Mouse não move
- Verifique se o Arduino está conectado e programado
- Confirme que PyAutoGUI tem permissões
- Teste: `import pyautogui; pyautogui.moveTo(500, 500)`

### Não detecta inimigos/flags
- Capture novas imagens das flags/inimigos no jogo
- Ajuste `CONFIDENCE` para 0.7 ou 0.6
- Verifique se as imagens estão na pasta correta

### Porta COM não encontrada
- Verifique Device Manager do Windows
- Reconecte o Arduino
- Use `[System.IO.Ports.SerialPort]::getportnames()` no PowerShell

### Tecla não pressiona
- Verifique se o comando KT está sendo enviado
- Teste manualmente: `ser.write(b"KT 9\n")`
- Confirme baud rate: 115200

## 📝 Desenvolvimento

### Adicionar Novo Inimigo

1. Capture imagem do inimigo: `nome_inimigo.png`
2. Salve em `enemy/`
3. Adicione no dicionário de prioridades:

```python
ENEMY_PRIORITY = {
    "witch": 3,
    "valkyrie": 2,
    "amazon": 1,
    "seu_inimigo": 2,  # Adicione aqui
}
```

4. Carregue a imagem:

```python
enemy_images = {
    # ... outros
    "seu_inimigo": os.path.abspath(os.path.join("..", "enemy", "seu_inimigo.png")),
}
```

### Adicionar Nova Rota

```python
NOVA_ROTA = [
    ("flag1", 5),   # flag, delay em segundos
    ("flag2", 8),
    ("flag3", 10),
]
```

## 📄 Licença

Este projeto é fornecido "como está" para fins educacionais.

## ⚠️ Aviso

Este bot é para fins educacionais e de automação pessoal. Use por sua conta e risco. O uso de bots em jogos online pode violar os Termos de Serviço do jogo.

## 🤝 Contribuindo

Sinta-se à vontade para abrir Issues ou Pull Requests com melhorias!

## 📧 Contato

- GitHub: [@Leozinrj](https://github.com/Leozinrj)
- Repositório: [botbt](https://github.com/Leozinrj/botbt)

---

**Desenvolvido com ❤️ usando Arduino Leonardo + Python**
