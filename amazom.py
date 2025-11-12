# amazom.py - PyAutoGUI + Arduino HID Controller
# Analisa a tela e envia comandos para o Arduino executar ações

import os
import time
import pyautogui as pg
import serial
from typing import Optional, Tuple

print("=" * 50)
print("AMAZOM - Automação com Arduino HID")
print("=" * 50)

# ===== CONFIGURAÇÕES =====
COM_PORT = "COM3"  # Altere para sua porta (COM3, COM7, etc.)
BAUD_RATE = 115200

# Detecção de imagem
CONFIDENCE = 0.8
LOCATE_TIMEOUT = 8.0
LOCATE_POLL = 0.15
RETRY_GAP = 5.0
MAX_RETRIES = 3

# Movimento do mouse
PAUSE_MS = 16
STEP_CAP = 12
MAX_CENTER_TIME = 6.0

# PyAutoGUI
pg.FAILSAFE = True
pg.PAUSE = 0

# ===== FUNÇÕES UTILITÁRIAS =====
def wait_exact(seconds: float, label: str = None, show: bool = True):
    """Aguarda tempo exato com feedback opcional"""
    start = time.monotonic()
    end = start + seconds
    
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.25, remaining))
    
    if show and seconds >= 1:
        real = time.monotonic() - start
        msg = f"[WAIT] {label}: " if label else "[WAIT] "
        print(f"{msg}{seconds:.2f}s (real: {real:.2f}s)")


def clamp(v: int, lo: int, hi: int) -> int:
    """Limita valor entre mínimo e máximo"""
    return max(lo, min(hi, v))


# ===== COMUNICAÇÃO SERIAL =====
def wait_ready(ser: serial.Serial, timeout: float = 2.0) -> bool:
    """Aguarda Arduino enviar READY ou OK"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        line = ser.readline().decode(errors="ignore").strip()
        if line in ("READY", "OK"):
            return True
    return False


def send_command(ser: serial.Serial, cmd: str, timeout: float = 1.2, retries: int = 2) -> bool:
    """Envia comando e aguarda OK"""
    for attempt in range(retries + 1):
        try:
            ser.reset_input_buffer()
        except Exception:
            pass
        
        ser.write((cmd + "\n").encode("ascii"))
        ser.flush()
        
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            resp = ser.readline().decode(errors="ignore").strip()
            if resp == "OK":
                return True
            if resp.startswith("ERR"):
                print(f"[ARDUINO] Erro: {resp} (comando: {cmd})")
                break
        
        if attempt < retries:
            time.sleep(0.1)
    
    print(f"[ARDUINO] Sem resposta para: {cmd}")
    return False


# ===== CONTROLE DO MOUSE =====
def move_relative(ser: serial.Serial, dx: int, dy: int) -> bool:
    """Move o mouse relativamente via Arduino"""
    dx = clamp(dx, -127, 127)
    dy = clamp(dy, -127, 127)
    return send_command(ser, f"M {dx} {dy}")


def move_to_position(ser: serial.Serial, target_x: int, target_y: int, 
                     pause_ms: int = PAUSE_MS, step_cap: int = STEP_CAP, 
                     max_time: float = MAX_CENTER_TIME) -> bool:
    """Move o mouse para posição exata com movimento gradual"""
    t0 = time.monotonic()
    last_pos = pg.position()
    stuck_count = 0
    
    while time.monotonic() - t0 < max_time:
        curr_x, curr_y = pg.position()
        dx = target_x - curr_x
        dy = target_y - curr_y
        
        if dx == 0 and dy == 0:
            return True
        
        # Movimento proporcional à distância
        dist = max(abs(dx), abs(dy))
        magnitude = min(step_cap, max(1, dist // 6))
        
        step_x = clamp(dx, -magnitude, magnitude)
        step_y = clamp(dy, -magnitude, magnitude)
        
        if not move_relative(ser, step_x, step_y):
            return False
        
        wait_exact(pause_ms / 1000.0, show=False)
        
        # Detecta travamento
        curr_pos = pg.position()
        if curr_pos == last_pos:
            stuck_count += 1
            if stuck_count >= 4 and magnitude > 1:
                # Tenta movimento pixel a pixel
                px = 1 if dx > 0 else (-1 if dx < 0 else 0)
                py = 1 if dy > 0 else (-1 if dy < 0 else 0)
                for _ in range(magnitude):
                    move_relative(ser, px, py)
                    wait_exact(0.006, show=False)
                stuck_count = 0
        else:
            stuck_count = 0
            last_pos = curr_pos
    
    print("[MOVE] Timeout ao centralizar mouse")
    return False


def click_left(ser: serial.Serial) -> bool:
    """Clique esquerdo"""
    return send_command(ser, "CL")


def click_right(ser: serial.Serial) -> bool:
    """Clique direito"""
    return send_command(ser, "CR")


def click_middle(ser: serial.Serial) -> bool:
    """Clique do meio"""
    return send_command(ser, "CM")


def double_click(ser: serial.Serial) -> bool:
    """Duplo clique esquerdo"""
    return send_command(ser, "CD")


def alt_click(ser: serial.Serial) -> bool:
    """Alt + clique esquerdo"""
    return send_command(ser, "AC")


# ===== CONTROLE DO TECLADO =====
def press_key(ser: serial.Serial, key: str) -> bool:
    """Pressiona tecla especial (ENTER, ESC, TAB, etc.)"""
    return send_command(ser, f"K {key}")


def type_text(ser: serial.Serial, text: str) -> bool:
    """Digita texto ASCII"""
    return send_command(ser, f"T {text}")


def press_combo(ser: serial.Serial, modifiers: str, key: str) -> bool:
    """Pressiona combinação de teclas (ex: CTRL, a)"""
    return send_command(ser, f"P {modifiers} {key}")


# ===== DETECÇÃO DE IMAGEM =====
def resolve_image(path: str) -> str:
    """Resolve caminho absoluto da imagem"""
    abspath = os.path.abspath(path)
    if not os.path.exists(abspath):
        print(f"[ERRO] Imagem não encontrada: {abspath}")
    return abspath


def locate_image_once(path: str, confidence: float = CONFIDENCE, 
                      timeout: float = LOCATE_TIMEOUT, 
                      poll: float = LOCATE_POLL) -> Optional[Tuple[int, int]]:
    """Tenta localizar imagem na tela uma vez"""
    filename = os.path.basename(path)
    path = resolve_image(path)
    
    print(f"[BUSCA] {filename} (timeout: {timeout:.1f}s, conf: {confidence:.2f})")
    
    deadline = time.monotonic() + timeout
    
    while time.monotonic() < deadline:
        try:
            # Tenta com confiança especificada
            c = pg.locateCenterOnScreen(path, confidence=confidence)
            if c:
                return (int(c.x), int(c.y))
        except Exception:
            pass
        
        try:
            # Tenta sem confiança
            c = pg.locateCenterOnScreen(path)
            if c:
                return (int(c.x), int(c.y))
        except Exception:
            pass
        
        try:
            # Tenta com grayscale
            c = pg.locateCenterOnScreen(path, confidence=confidence, grayscale=True)
            if c:
                return (int(c.x), int(c.y))
        except Exception:
            pass
        
        wait_exact(poll, show=False)
    
    return None


def locate_image_with_retry(path: str, retries: int = MAX_RETRIES, 
                            gap: float = RETRY_GAP) -> Optional[Tuple[int, int]]:
    """Tenta localizar imagem com re-tentativas"""
    pos = locate_image_once(path)
    if pos:
        return pos
    
    for i in range(retries):
        print(f"[RETRY] Tentativa {i+1}/{retries} após {gap:.0f}s...")
        wait_exact(gap, show=False)
        pos = locate_image_once(path)
        if pos:
            return pos
    
    return None


# ===== AÇÕES COMBINADAS =====
def find_and_click(ser: serial.Serial, image_path: str, 
                  click_type: str = "left", wait_after: float = 0) -> bool:
    """Encontra imagem, move mouse e clica"""
    pos = locate_image_with_retry(image_path)
    
    if not pos:
        print(f"[ERRO] Imagem não encontrada: {os.path.basename(image_path)}")
        return False
    
    x, y = pos
    print(f"[OK] Encontrado em ({x},{y}) - clicando ({click_type})...")
    
    # Define estado busy
    send_command(ser, "B1")
    
    # Move para posição
    if not move_to_position(ser, x, y):
        print("[ERRO] Falha ao mover mouse")
        send_command(ser, "B0")
        return False
    
    wait_exact(0.05, show=False)
    
    # Executa clique
    if click_type == "left":
        click_left(ser)
    elif click_type == "right":
        click_right(ser)
    elif click_type == "middle":
        click_middle(ser)
    elif click_type == "double":
        double_click(ser)
    elif click_type == "alt":
        alt_click(ser)
    
    # Volta para idle
    send_command(ser, "B0")
    
    # Aguarda se necessário
    if wait_after > 0:
        wait_exact(wait_after, label=os.path.basename(image_path))
    
    return True


# ===== EXEMPLO DE USO =====
def main():
    """Função principal - exemplo de uso"""
    input("Pressione ENTER para iniciar...")
    
    try:
        with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"[SERIAL] Conectado em {COM_PORT} @ {BAUD_RATE} baud")
            
            # Aguarda Arduino inicializar
            wait_exact(1.8, show=False)
            ser.reset_input_buffer()
            
            if not wait_ready(ser, 2.0):
                print("[ERRO] Arduino não respondeu")
                return
            
            print("[OK] Arduino pronto!")
            
            # ===== EXEMPLO DE AUTOMAÇÃO =====
            # Descomente e adapte conforme seu projeto:
            
            # # Encontra e clica em uma imagem
            # if not find_and_click(ser, "botao.png", "left", wait_after=2):
            #     return
            
            # # Digita texto
            # type_text(ser, "Olá, mundo!")
            # press_key(ser, "ENTER")
            
            # # Combinação de teclas
            # press_combo(ser, "CTRL", "a")  # Ctrl+A
            # press_combo(ser, "CTRL", "c")  # Ctrl+C
            
            print("[OK] Automação concluída!")
            
    except serial.SerialException as e:
        print(f"[ERRO] Serial: {e}")
    except KeyboardInterrupt:
        print("\n[STOP] Cancelado pelo usuário (Ctrl+C)")


if __name__ == "__main__":
    main()
