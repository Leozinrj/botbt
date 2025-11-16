# Instruções de Uso - Sistema de Automação AMAZOM

## 🎮 Como Funciona

Este sistema automatiza batalhas usando:
- **Python**: Detecta imagens na tela (flags e batalhas)
- **Arduino**: Executa cliques do mouse e teclas via USB HID

## 📋 Pré-requisitos

### Hardware
- Arduino Leonardo, Micro ou Pro Micro (suporta Mouse.h e Keyboard.h)
- Cabo USB para conectar o Arduino ao PC

### Software
1. **Python 3.x** instalado
2. **Bibliotecas Python**:
   ```powershell
   pip install pyautogui pyserial pillow
   ```

3. **PlatformIO** (para programar o Arduino)
   - Já configurado na pasta `amazon/`

## 🔧 Configuração

### 1. Programar o Arduino

1. Abra o projeto PlatformIO em `c:\Users\leoru\Documents\PlatformIO\Projects\amazon\`
2. Compile e envie o código para o Arduino (arquivo `src/main.cpp`)
3. Anote a porta COM do Arduino (ex: COM3)

**Para descobrir a porta:**
- Gerenciador de Dispositivos → Portas (COM & LPT)
- Procure por "Arduino" ou "USB Serial Device"

### 2. Configurar o Python

Edite `amazom.py` e altere a linha 9 se necessário:
```python
COM_PORT = "COM3"  # Altere para sua porta Arduino
```

### 3. Preparar as Imagens

Certifique-se que estas imagens estão na pasta `d:\amazom\`:
- `flag1.png` - Primeira flag/objetivo
- `flag2.png` - Segunda flag
- `flag3.png` - Terceira flag
- `flag4.png` - Quarta flag
- `battle.png` - Tela de batalha
- `amazon.png` - Inimigo Amazon (dentro da tela de batalha)

**Dica**: Use capturas de tela nítidas e recorte apenas a parte relevante.

## 🚀 Executar

1. **Feche qualquer monitor serial** que esteja usando a porta COM do Arduino

2. Execute o script Python:
   ```powershell
   cd d:\amazom
   python amazom.py
   ```

3. Pressione **ENTER** quando solicitado

4. O script começará automaticamente:
   - Busca e clica em flag1
   - Monitora batalha e combate Amazon (ESPAÇO → 7s → \\)
   - Clica em flag2, aguarda 10s
   - Repete batalha
   - Clica em flag3, aguarda 10s
   - Repete batalha
   - Clica em flag4, aguarda 10s
   - **Reinicia o ciclo**

5. Para interromper: **Ctrl+C** ou mova o mouse para o canto superior esquerdo (FAILSAFE)

## 🎯 Fluxo de Execução

```
┌─────────────────────────────────────┐
│  1. Busca flag1.png                 │
│  2. Clica no centro da flag1        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. Monitora battle.png             │
│  4. Se amazon.png aparecer:         │
│     - Pressiona ESPAÇO              │
│     - Aguarda 7 segundos            │
│     - Pressiona \                   │
│  5. Repete até limpar               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  6. Busca flag2.png                 │
│  7. Clica e aguarda 10 segundos     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  8. Repete batalha (passos 3-5)     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  9. Flag3 → Aguarda 10s             │
│ 10. Batalha                         │
│ 11. Flag4 → Aguarda 10s             │
│ 12. REINICIA DO INÍCIO              │
└─────────────────────────────────────┘
```

## 🔍 Solução de Problemas

### Arduino não responde
- Verifique se a porta COM está correta
- Confirme que o Arduino foi programado com o código correto
- Feche outros programas que possam estar usando a porta (Monitor Serial, etc.)

### Imagens não são encontradas
- Certifique-se que as imagens estão na pasta `d:\amazom\`
- Tire screenshots nítidos com resolução nativa
- Reduza o valor de `CONFIDENCE` no código (linha 11) para 0.7 ou 0.6

### Mouse não clica no lugar certo
- O Arduino usa movimento **relativo**, não absoluto
- Verifique se o mouse está livre para mover (sem interferências físicas)
- Ajuste a sensibilidade do mouse no Windows

### Comandos de teclado não funcionam
- Certifique-se que o jogo/programa aceita entrada de teclado
- Verifique se o foco está na janela correta
- Alguns jogos bloqueiam entrada de dispositivos HID virtuais

## ⚙️ Personalização

### Ajustar Tempos

No arquivo `amazom.py`:
- Linha 12: `BATTLE_CHECK_INTERVAL = 0.5` - Frequência de verificação da batalha
- Linha 13: `LOCATE_TIMEOUT = 10.0` - Tempo máximo para encontrar imagens
- Na função `wait_for_battle_clear`: `wait_exact(7.0)` - Tempo de combate
- Nos passos das flags: `wait_exact(10.0)` - Tempo após clicar na flag

### Ajustar Confiança de Detecção

Linha 11:
```python
CONFIDENCE = 0.8  # 0.6 = mais permissivo, 0.95 = mais restritivo
```

### Mudar Porta COM

Linha 9:
```python
COM_PORT = "COM5"  # Mude para sua porta
```

## 📝 Protocolo de Comunicação Arduino

O Arduino aceita os seguintes comandos via Serial (9600 baud):

- `CLICK:dx,dy` - Move mouse (dx,dy) pixels e clica
- `SPACE` - Pressiona tecla ESPAÇO
- `BACKSLASH` - Pressiona tecla \

Todos os comandos retornam `OK` quando executados com sucesso.

## 🛡️ Segurança

- **FAILSAFE**: Mova o mouse para o canto superior esquerdo para parar
- **Ctrl+C**: Interrompe o script a qualquer momento
- O Arduino só executa comandos específicos (não há risco de comandos indesejados)

## 📧 Suporte

Em caso de problemas:
1. Verifique as mensagens de erro no console
2. Confirme que todas as imagens existem
3. Teste manualmente se o Arduino responde via Monitor Serial
