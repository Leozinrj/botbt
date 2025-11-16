# AMAZOM - Automação com Arduino HID

Sistema de automação que usa Python para análise de tela (PyAutoGUI) e Arduino Pro Micro/Leonardo como controlador HID (Mouse + Keyboard).

## 🎯 Características

- ✅ **Detecção de imagem** na tela com PyAutoGUI
- ✅ **Arduino como HID nativo** - impossível de detectar como bot
- ✅ **Controle de mouse** via comandos serial
- ✅ **Controle de teclado** com teclas especiais e combinações
- ✅ **Sistema de retry** para busca de imagens
- ✅ **LED de status** no Arduino

## 📋 Requisitos

### Hardware
- Arduino Leonardo ou Pro Micro (ATmega32u4)
- Cabo USB

### Software
- Python 3.7+
- Arduino IDE 1.8+ ou 2.x
- Windows/Linux/Mac

## 🔧 Instalação

### 1. Configurar Python

```bash
# Criar ambiente virtual (opcional mas recomendado)
python -m venv venv

# Ativar ambiente (Windows)
venv\Scripts\activate

# Ativar ambiente (Linux/Mac)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar Arduino

1. Abra `amazom.ino` no Arduino IDE
2. Selecione sua placa:
   - **Tools > Board > Arduino Leonardo** ou
   - **Tools > Board > SparkFun Pro Micro**
3. Selecione a porta serial: **Tools > Port > COMx** (Windows) ou **/dev/ttyACMx** (Linux)
4. Faça o upload do código

### 3. Identificar porta serial

**Windows:**
```powershell
# No Device Manager ou via PowerShell
Get-WmiObject Win32_SerialPort | Select-Object Name,DeviceID
```

**Linux/Mac:**
```bash
ls /dev/tty*
# Procure por /dev/ttyACM0 ou /dev/ttyUSB0
```

Edite `amazom.py` e ajuste a variável `COM_PORT`:
```python
COM_PORT = "COM3"  # Windows
# ou
COM_PORT = "/dev/ttyACM0"  # Linux/Mac
```

## 🚀 Uso

### Execução básica

```bash
python amazom.py
```

### Exemplo de automação

```python
from amazom import *

# Conectar ao Arduino
with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser:
    wait_ready(ser)
    
    # Encontrar e clicar em imagem
    find_and_click(ser, "botao.png", "left", wait_after=2)
    
    # Digitar texto
    type_text(ser, "Hello, World!")
    press_key(ser, "ENTER")
    
    # Combinação de teclas
    press_combo(ser, "CTRL", "s")  # Ctrl+S para salvar
```

## 📡 Protocolo de Comandos

### Comandos de Mouse
| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `M dx dy` | Move relativo | `M 10 -5` |
| `CL` | Clique esquerdo | `CL` |
| `CR` | Clique direito | `CR` |
| `CM` | Clique do meio | `CM` |
| `CD` | Duplo clique | `CD` |
| `AC` | Alt + clique | `AC` |

### Comandos de Teclado
| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `K <key>` | Tecla especial | `K ENTER` |
| `T <texto>` | Digitar texto | `T hello` |
| `P <mods> <key>` | Combinação | `P CTRL s` |

### Teclas Especiais Suportadas
- `ENTER`, `ESC`, `TAB`, `SPACE`, `BKSP`, `DEL`
- `UP`, `DOWN`, `LEFT`, `RIGHT`
- `HOME`, `END`, `PGUP`, `PGDN`
- `F1` até `F12`

### Modificadores para Combinações
- `CTRL`, `SHIFT`, `ALT`, `WIN`/`GUI`

### Controle
| Comando | Descrição |
|---------|-----------|
| `B1` | Ativa modo busy (LED fixo) |
| `B0` | Modo idle (LED piscando) |
| `S <ms>` | Sleep em milissegundos |

## 🔍 Configurações

Edite as variáveis no início de `amazom.py`:

```python
# Porta serial
COM_PORT = "COM3"

# Detecção de imagem
CONFIDENCE = 0.8         # Confiança 0.0-1.0
LOCATE_TIMEOUT = 8.0     # Timeout por tentativa (segundos)
MAX_RETRIES = 3          # Número de re-tentativas

# Movimento do mouse
STEP_CAP = 12            # Tamanho máximo de passo
MAX_CENTER_TIME = 6.0    # Timeout para centralizar
```

## 💡 Dicas

1. **Tire screenshots** das áreas que quer detectar
2. **Use alta confiança** (0.9+) para maior precisão
3. **LED pisca** = Arduino ocioso, **LED fixo** = executando
4. **Ctrl+C** interrompe a execução
5. **PyAutoGUI FAILSAFE**: Mova o mouse para o canto superior esquerdo para abortar

## 🐛 Troubleshooting

**Arduino não responde:**
- Verifique a porta COM
- Aguarde 2s após conectar (tempo de enumeração USB)
- Reset manual no Arduino

**Imagem não encontrada:**
- Verifique se o arquivo existe
- Reduza `CONFIDENCE` para 0.7-0.8
- Use screenshots com boa resolução
- Tente com `grayscale=True`

**Mouse não se move:**
- Confirme que o Arduino enviou "OK"
- Verifique baudrate (115200)
- Teste movimento manual via Serial Monitor

## 📝 Licença

Código livre para uso pessoal e educacional.

## 🤝 Contribuições

Melhorias são bem-vindas! Abra issues ou pull requests.

---

**Autor:** Leozinrj  
**Repositório:** https://github.com/Leozinrj/amazom
